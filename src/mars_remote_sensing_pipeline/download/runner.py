"""Run download jobs concurrently and report progress to stdout."""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from mars_remote_sensing_pipeline.download.planner import Job
from mars_remote_sensing_pipeline.ode import products
from mars_remote_sensing_pipeline.ode.client import ODEClient
from mars_remote_sensing_pipeline.storage.writer import write_jsonl

MAX_WORKERS = 6


@dataclass
class RunResult:
    """Summary of a download run.

    Attributes:
        ran: Number of jobs executed.
        rows: Total product records written.
        empty: Number of jobs that matched no products.
        failed: Number of jobs that raised an error.
    """

    ran: int = 0
    rows: int = 0
    empty: int = 0
    failed: int = 0


def _run_one(
    client: ODEClient,
    job: Job,
    loc: str,
    min_obs_time: str | None,
    max_obs_time: str | None,
) -> tuple[Job, int, Exception | None]:
    """Download and write one job, counting first to skip empty fetches.

    An output file is always written, empty included, so a later run can skip
    it. Nothing is written when the job fails.

    Args:
        client: The shared ODE client.
        job: The feature and instrument set to download.
        loc: The ODE containment mode.
        min_obs_time: Optional minimum UTC observation time.
        max_obs_time: Optional maximum UTC observation time.

    Returns:
        A tuple (job, rows_written, error). Rows is -1 when the job failed.
    """
    try:
        total = products.count(
            client,
            job.feature,
            job.instrument_set,
            loc=loc,
            min_obs_time=min_obs_time,
            max_obs_time=max_obs_time,
        )
        records = (
            products.fetch_products(
                client,
                job.feature,
                job.instrument_set,
                loc=loc,
                total=total,
                min_obs_time=min_obs_time,
                max_obs_time=max_obs_time,
            )
            if total
            else []
        )
        written = write_jsonl(job.output_path, records)
        return job, written, None
    except Exception as exc:
        return job, -1, exc


def run_jobs(
    client: ODEClient,
    jobs: Sequence[Job],
    *,
    loc: str = "o",
    workers: int = 4,
    min_obs_time: str | None = None,
    max_obs_time: str | None = None,
) -> RunResult:
    """Execute jobs on a bounded thread pool, printing progress and a summary.

    Args:
        client: The shared ODE client.
        jobs: The jobs to run.
        loc: The ODE containment mode.
        workers: Requested worker count, clamped to the safe maximum.
        min_obs_time: Optional minimum UTC observation time.
        max_obs_time: Optional maximum UTC observation time.

    Returns:
        A summary of the run.
    """
    result = RunResult()
    if not jobs:
        print("nothing to do")
        return result
    worker_count = max(1, min(workers, MAX_WORKERS))
    total_jobs = len(jobs)
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = [
            pool.submit(_run_one, client, job, loc, min_obs_time, max_obs_time)
            for job in jobs
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            job, rows, error = future.result()
            label = f"{job.feature.name} [{job.instrument_set.key}]"
            if error is not None:
                result.failed += 1
                print(f"[{index}/{total_jobs}] {label} ERROR: {error}")
                continue
            result.ran += 1
            result.rows += rows
            if rows == 0:
                result.empty += 1
            print(f"[{index}/{total_jobs}] {label} -> {rows} rows")
    print(
        f"done: {result.ran} jobs, {result.rows} rows, "
        f"{result.empty} empty, {result.failed} failed"
    )
    return result

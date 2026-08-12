"""Run download jobs concurrently, emitting structured progress events."""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed

from download import configs
from download.models import Job, JobOutcome, ProgressEvent, RunSummary
from download.ode import products
from download.ode.client import ODEClient
from download.storage.writer import write_jsonl


class DownloadRunner:
    """Executes download jobs on a bounded thread pool.

    The runner never writes to the console. It yields a ProgressEvent as each
    job finishes and exposes a RunSummary once the run is complete, leaving all
    rendering to the caller.
    """

    def __init__(
        self,
        client: ODEClient,
        *,
        loc: str = configs.DEFAULT_LOC,
        workers: int = configs.DEFAULT_WORKERS,
        min_obs_time: str | None = None,
        max_obs_time: str | None = None,
    ) -> None:
        """Create a runner.

        Args:
            client: The shared ODE client.
            loc: The ODE containment mode.
            workers: Requested worker count, clamped to the safe maximum.
            min_obs_time: Optional minimum UTC observation time.
            max_obs_time: Optional maximum UTC observation time.

        Returns:
            None.
        """
        self._client = client
        self._loc = loc
        self._workers = max(1, min(workers, configs.MAX_WORKERS))
        self._min_obs_time = min_obs_time
        self._max_obs_time = max_obs_time
        self._summary: RunSummary | None = None

    @property
    def summary(self) -> RunSummary | None:
        """Return the summary of the last completed run.

        Returns:
            The summary, or None if no run has finished yet.
        """
        return self._summary

    @property
    def workers(self) -> int:
        """Return the effective worker count after clamping.

        Returns:
            The number of concurrent workers used.
        """
        return self._workers

    def run(self, jobs: Sequence[Job]) -> Iterator[ProgressEvent]:
        """Execute jobs concurrently, yielding progress as each finishes.

        Args:
            jobs: The jobs to run.

        Yields:
            One ProgressEvent per finished job, in completion order.
        """
        started = time.monotonic()
        ran = 0
        rows = 0
        empty = 0
        failed = 0
        total = len(jobs)
        if total:
            with ThreadPoolExecutor(max_workers=self._workers) as pool:
                futures = [pool.submit(self._run_one, job) for job in jobs]
                for completed, future in enumerate(as_completed(futures), start=1):
                    outcome = future.result()
                    if outcome.failed:
                        failed += 1
                    else:
                        ran += 1
                        rows += outcome.rows
                        if outcome.rows == 0:
                            empty += 1
                    yield ProgressEvent(
                        completed=completed,
                        total=total,
                        elapsed=time.monotonic() - started,
                        outcome=outcome,
                        rows=rows,
                        failed=failed,
                    )
        self._summary = RunSummary(
            ran=ran,
            rows=rows,
            empty=empty,
            failed=failed,
            elapsed=time.monotonic() - started,
        )

    def _run_one(self, job: Job) -> JobOutcome:
        """Download and write one job, counting first to skip empty fetches.

        An output file is always written, empty included, so a later run can
        skip it. Nothing is written when the job fails.

        Args:
            job: The feature and instrument set to download.

        Returns:
            The outcome, carrying the error when the job failed.
        """
        try:
            total = products.count(
                self._client,
                job.feature,
                job.instrument_set,
                loc=self._loc,
                min_obs_time=self._min_obs_time,
                max_obs_time=self._max_obs_time,
            )
            records = (
                products.fetch_products(
                    self._client,
                    job.feature,
                    job.instrument_set,
                    loc=self._loc,
                    total=total,
                    min_obs_time=self._min_obs_time,
                    max_obs_time=self._max_obs_time,
                )
                if total
                else []
            )
            written = write_jsonl(job.output_path, records)
            return JobOutcome(job=job, rows=written)
        except Exception as exc:
            return JobOutcome(job=job, rows=0, error=exc)

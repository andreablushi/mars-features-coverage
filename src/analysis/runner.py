"""Run coverage jobs concurrently, emitting structured progress events.

Each feature is an independent CPU-bound job, so the work runs on a process
pool rather than the thread pool the download stage uses. A worker writes its
own parquet files and hands back only a count, keeping the millions of event
rows a full catalogue produces out of the parent process entirely.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed

from analysis import configs
from analysis.computation import coverage
from analysis.loader import writer
from analysis.loader.records import load_feature
from analysis.models import schemas
from analysis.models.job import CoverageJob, JobOutcome
from analysis.models.progress import RunSummary
from common.models.progress import ProgressEvent


def run_job(job: CoverageJob) -> JobOutcome:
    """Compute and write coverage for one feature.

    The events are written before the summary, so a summary on disk means the
    whole feature finished and a later run can skip it.

    Args:
        job: The feature to compute.

    Returns:
        The outcome, carrying the error when the job failed.
    """
    try:
        data = load_feature(job.source)
        if data is None:
            return JobOutcome(job=job)
        events, summaries = coverage.compute(data.box, data.observations)
        writer.write(events, schemas.EVENTS, job.events_path)
        writer.write(summaries, schemas.SUMMARY, job.summary_path)
        return JobOutcome(job=job, events=len(events))
    except Exception as exc:
        return JobOutcome(job=job, error=exc)


class CoverageRunner:
    """Computes coverage for many features on a bounded process pool.

    The runner never writes to the console. It yields a ProgressEvent as each
    feature finishes and exposes a RunSummary once the run is complete, leaving
    all rendering to the caller.
    """

    def __init__(self, *, workers: int = configs.DEFAULT_WORKERS) -> None:
        """Create a runner.

        Args:
            workers: Requested worker count, at least one.

        Returns:
            None.
        """
        self._workers = max(1, workers)
        self._summary = RunSummary(computed=0, failed=0, events=0, elapsed=0.0)

    @property
    def workers(self) -> int:
        """Return the effective worker count.

        Returns:
            The number of concurrent workers used.
        """
        return self._workers

    @property
    def summary(self) -> RunSummary:
        """Return the summary of the last run.

        Returns:
            The summary, zeroed until a run has finished.
        """
        return self._summary

    def run(self, jobs: Sequence[CoverageJob]) -> Iterator[ProgressEvent]:
        """Execute jobs concurrently, yielding progress as each finishes.

        Args:
            jobs: The features to compute.

        Yields:
            One ProgressEvent per finished feature, in completion order.
        """
        started = time.monotonic()
        computed = failed = events = 0
        pool = ProcessPoolExecutor(max_workers=self._workers)
        try:
            futures = [pool.submit(run_job, job) for job in jobs]
            for completed, future in enumerate(as_completed(futures), start=1):
                outcome = future.result()
                if outcome.failed:
                    failed += 1
                else:
                    computed += 1
                    events += outcome.events
                yield ProgressEvent(completed=completed, outcome=outcome)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
            self._summary = RunSummary(
                computed=computed,
                failed=failed,
                events=events,
                elapsed=time.monotonic() - started,
            )

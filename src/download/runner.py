"""Run download jobs concurrently, emitting structured progress events."""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed

from common.jsonl import write_jsonl
from common.models.progress import ProgressEvent
from download import configs
from download.api import products
from download.api.client import ODEClient
from download.models.job import Job, JobOutcome
from download.models.progress import RunSummary


class DownloadRunner:
    """Executes download jobs on a bounded thread pool.

    The runner never writes to the console. It yields a ProgressEvent as each
    job finishes and exposes a RunSummary once the run is complete, leaving all
    rendering to the caller.
    """

    def __init__(
        self, client: ODEClient, *, workers: int = configs.DEFAULT_WORKERS
    ) -> None:
        """Create a runner.

        Args:
            client: The shared ODE client.
            workers: Requested worker count, clamped to the safe maximum.

        Returns:
            None.
        """
        self._client = client
        self._workers = max(1, min(workers, configs.MAX_WORKERS))
        self._summary = RunSummary(ran=0, failed=0, elapsed=0.0)

    @property
    def summary(self) -> RunSummary:
        """Return the summary of the last run.

        Returns:
            The summary, zeroed until a run has finished.
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
        failed = 0
        pool = ThreadPoolExecutor(max_workers=self._workers)
        try:
            futures = [pool.submit(self._run_one, job) for job in jobs]
            for completed, future in enumerate(as_completed(futures), start=1):
                outcome = future.result()
                if outcome.failed:
                    failed += 1
                else:
                    ran += 1
                yield ProgressEvent(completed=completed, outcome=outcome)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
            self._summary = RunSummary(
                ran=ran, failed=failed, elapsed=time.monotonic() - started
            )

    def _run_one(self, job: Job) -> JobOutcome:
        """Download and write one job.

        An output file is always written, empty included, so a later run can
        skip it. Nothing is written when the job fails.

        Args:
            job: The feature and instrument set to download.

        Returns:
            The outcome, carrying the error when the job failed.
        """
        try:
            records = products.fetch_products(
                self._client, job.feature, job.instrument_set
            )
            write_jsonl(job.output_path, records)
            return JobOutcome(job=job)
        except Exception as exc:
            return JobOutcome(job=job, error=exc)

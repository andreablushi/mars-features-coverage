"""Run coverage jobs concurrently, emitting structured progress events.

Each instrument set is an independent CPU-bound job, so the work runs on a
process pool rather than the thread pool the download stage uses. Splitting per
set rather than per feature keeps the pool busy: a feature's sets differ in size
by orders of magnitude, so one job per feature leaves a single worker grinding
through the largest set while the rest idle.

A worker writes its own files and hands back only a count, keeping the millions
of event rows a full catalogue produces out of the parent process entirely.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed

from analysis import configs
from analysis.computation import coverage, prepare
from analysis.computation.region import FeatureRegion
from analysis.loader import geometry, records, writer
from analysis.models.feature import FeatureBox
from analysis.models.job import CoverageJob, JobOutcome
from analysis.models.progress import RunSummary
from analysis.models.projected import ProjectedObservation
from analysis.models.schemas import EVENTS, SUMMARY
from common.models.progress import ProgressEvent


def run_job(job: CoverageJob) -> JobOutcome:
    """Compute and write coverage for one feature and instrument set.

    The events are written before the summary, so a summary on disk means the
    whole set finished and a later run can skip it.

    Args:
        job: The instrument set to compute.

    Returns:
        The outcome, carrying the error when the job failed.
    """
    try:
        prepared = _prepare(job)
        if prepared is None:
            return JobOutcome(job=job)
        box, region, projected = prepared
        events, summary = coverage.compute(box, region, projected)
        writer.write(events, EVENTS, job.events_path)
        writer.write([summary], SUMMARY, job.summary_path)
        return JobOutcome(job=job, events=len(events))
    except Exception as exc:
        return JobOutcome(job=job, error=exc)


def _prepare(
    job: CoverageJob,
) -> tuple[FeatureBox, FeatureRegion, list[ProjectedObservation]] | None:
    """Load projected footprints, from the cache when it is still valid.

    Args:
        job: The instrument set being computed.

    Returns:
        The feature box, its projected region, and the projected observations,
        or None when the set holds nothing usable.
    """
    cached = geometry.load(job.geometry_path, job.source)
    if cached is not None:
        box, projected = cached
        return box, _region(box), projected
    loaded = records.load_set(job.source)
    if loaded is None:
        return None
    box, observations = loaded
    region = _region(box)
    projected = prepare.project(region, observations)
    geometry.save(job.geometry_path, box, projected)
    return box, region, projected


def _region(box: FeatureBox) -> FeatureRegion:
    """Project one feature's bounding box.

    Args:
        box: The feature to project.

    Returns:
        The projected region.
    """
    return FeatureRegion(box.min_lat, box.max_lat, box.west_lon, box.east_lon)


class CoverageRunner:
    """Computes coverage for many instrument sets on a bounded process pool.

    The runner never writes to the console. It yields a ProgressEvent as each
    set finishes and exposes a RunSummary once the run is complete, leaving all
    rendering to the caller.
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
            jobs: The instrument sets to compute.

        Yields:
            One ProgressEvent per finished set, in completion order.
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

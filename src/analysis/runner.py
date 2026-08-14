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


def run_job(
    job: CoverageJob, cumulative_union: bool = configs.DEFAULT_CUMULATIVE_UNION
) -> JobOutcome:
    """Compute and write coverage for one feature and instrument set.

    The events are written before the summary, so a summary on disk means the
    whole set finished and a later run can skip it.

    Args:
        job: The instrument set to compute.
        cumulative_union: Whether to accumulate the running union.

    Returns:
        The outcome, carrying the error when the job failed.
    """
    try:
        prepared = _prepare(job)
        if prepared is None:
            return JobOutcome(job=job)
        box, region, projected, discarded = prepared
        if not projected:
            return JobOutcome(job=job, discarded=discarded)
        events, summary = coverage.compute(
            box, region, projected, cumulative_union=cumulative_union
        )
        writer.write(events, EVENTS, job.events_path)
        writer.write([summary], SUMMARY, job.summary_path)
        return JobOutcome(job=job, events=len(events), discarded=discarded)
    except Exception as exc:
        return JobOutcome(job=job, error=exc)


def _prepare(
    job: CoverageJob,
) -> tuple[FeatureBox, FeatureRegion, list[ProjectedObservation], int] | None:
    """Load projected footprints, from the cache when it is still valid.

    A cache hit reports no discards. Only a set that yielded something is ever
    cached, so the sets whose discards matter are always read afresh.

    Args:
        job: The instrument set being computed.

    Returns:
        The feature box, its projected region, the projected observations, and
        how many stored records were discarded for carrying nothing usable or
        for missing the feature, or None when the set holds no records at all.
    """
    cached = geometry.load(job.geometry_path, job.source)
    if cached is not None:
        box, projected = cached
        return box, _region(box), projected, 0
    loaded = records.load_set(job.source)
    if loaded is None:
        return None
    box, observations, discarded = loaded
    region = _region(box)
    projected, missed = prepare.project(region, observations)
    if projected:
        geometry.save(job.geometry_path, box, projected)
    return box, region, projected, discarded + missed


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

    def __init__(
        self,
        *,
        workers: int = configs.DEFAULT_WORKERS,
        cumulative_union: bool = configs.DEFAULT_CUMULATIVE_UNION,
    ) -> None:
        """Create a runner.

        Args:
            workers: How many sets to compute at once.
            cumulative_union: Whether each job accumulates the running union.

        Returns:
            None.
        """
        self._workers = workers
        self._cumulative_union = cumulative_union
        self._summary = RunSummary(
            computed=0, empty=0, failed=0, events=0, discarded=0, elapsed=0.0
        )

    @property
    def workers(self) -> int:
        """Return the worker count this runner uses.

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
        computed = empty = failed = events = discarded = 0
        pool = ProcessPoolExecutor(max_workers=self._workers)
        try:
            futures = [
                pool.submit(run_job, job, self._cumulative_union) for job in jobs
            ]
            for completed, future in enumerate(as_completed(futures), start=1):
                outcome = future.result()
                discarded += outcome.discarded
                if outcome.failed:
                    failed += 1
                elif outcome.empty:
                    empty += 1
                else:
                    computed += 1
                    events += outcome.events
                yield ProgressEvent(completed=completed, outcome=outcome)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
            self._summary = RunSummary(
                computed=computed,
                empty=empty,
                failed=failed,
                events=events,
                discarded=discarded,
                elapsed=time.monotonic() - started,
            )

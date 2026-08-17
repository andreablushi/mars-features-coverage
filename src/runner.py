"""Running the pipeline's work: one pooled runner, and the two halves it drives."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import (
    Executor,
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from contextlib import closing
from pathlib import Path
from typing import TypeVar

from rich.console import Console

import configs
from analysis import planner as coverage_planner
from analysis.tasks import run_job as compute_coverage
from cli import progress
from cli.console import describe_coverage, describe_download
from download import planner as download_planner
from download.api import catalog as ode_catalog
from download.api.client import ODEClient
from download.selection.instruments import verify_sets
from download.tasks import run_job as download_set
from models.job import CoverageOutcome, DownloadOutcome, DownloadPlan
from models.progress import CoverageSummary, DownloadSummary, Outcome, ProgressEvent
from models.settings import DownloadSettings, PipelineSettings
from storage import catalog, layout

Job = TypeVar("Job")


def run(
    jobs: Sequence[Job], execute: Callable[[Job], Outcome], pool: Executor
) -> Iterator[ProgressEvent]:
    """Run every job on the pool, yielding progress as each one finishes.

    Threads suit work waiting on the network and processes work bound to a
    core, so the pool is the caller's choice and only this is shared.

    Args:
        jobs: The work to run.
        execute: What to call for one job, returning its outcome. It must never
            raise, since a stage reports a failure as an outcome rather than by
            stopping the run, and it must be picklable when the pool runs on
            processes, which rules out a lambda or a local function.
        pool: The pool to run on, owned and shut down by the caller.

    Yields:
        One event per finished job, in completion order.
    """
    futures = [pool.submit(execute, job) for job in jobs]
    for completed, future in enumerate(as_completed(futures), start=1):
        yield ProgressEvent(completed=completed, outcome=future.result())


def _collecting(events: Iterator[ProgressEvent], into: list) -> Iterator[ProgressEvent]:
    """Keep every outcome while passing its event on.

    Args:
        events: The runner's progress events.
        into: The list the outcomes are appended to.

    Yields:
        Each event, unchanged.
    """
    for event in events:
        into.append(event.outcome)
        yield event


def _submitting(
    events: Iterator[ProgressEvent],
    pool: ProcessPoolExecutor,
    started: list[Future[CoverageOutcome]],
    *,
    force: bool,
) -> Iterator[ProgressEvent]:
    """Pass download events through, starting each set's coverage as it lands.

    Args:
        events: The download runner's progress events.
        pool: The process pool the coverage jobs run on.
        started: The coverage futures, appended to as they are submitted.
        force: Whether to recompute a set that is already done.

    Yields:
        Each event, unchanged.
    """
    for event in events:
        if not event.outcome.failed:
            source = event.outcome.job.output_path
            if source.stat().st_size:
                for job in coverage_planner.build_plan([source], force=force).jobs:
                    started.append(pool.submit(compute_coverage, job))
        yield event


def _drain(started: Sequence[Future[CoverageOutcome]]) -> Iterator[ProgressEvent]:
    """Yield a progress event as each coverage job finishes.

    Args:
        started: The coverage futures to wait on.

    Yields:
        One event per finished job, in completion order.
    """
    for completed, future in enumerate(started, start=1):
        yield ProgressEvent(completed=completed, outcome=future.result())


def _pending(plan: DownloadPlan) -> list[Path]:
    """Return the sets already on disk that this run will not download again.

    A set the download is about to rewrite is measured once it lands rather
    than now, so it is left out here and cannot be computed twice.

    Args:
        plan: The download plan, naming every file this run will write.

    Returns:
        The stored metadata files to weigh for the coverage backlog.
    """
    rewriting = {job.output_path for job in plan.jobs}
    return [source for source in layout.find_sets() if source not in rewriting]


def survey(
    download: DownloadSettings, pipeline: PipelineSettings, console: Console
) -> tuple[DownloadSummary, list[CoverageOutcome]]:
    """Download every set still missing and measure every set not yet measured.

    Both gaps are filled by the same run: what is already on disk is submitted
    before the first download lands, so a set an earlier run downloaded but
    never measured is picked up here rather than waiting to be fetched again.

    Args:
        download: The settled download choices.
        pipeline: The settled choices for the run as a whole.
        console: The console to render on.

    Returns:
        The download half's totals and every finished coverage outcome.
    """
    started_at = time.monotonic()
    futures: list[Future[CoverageOutcome]] = []
    fetched: list[DownloadOutcome] = []
    with ODEClient() as client:
        refresh = pipeline.refresh_catalog
        features = ode_catalog.load_features(client, refresh=refresh)
        verify_sets(
            download.instrument_sets,
            ode_catalog.load_instrument_sets(client, refresh=refresh),
        )
        plan = download_planner.build_plan(
            features,
            download.instrument_sets,
            names=download.feature_names,
            force=pipeline.force,
        )
        backlog = coverage_planner.build_plan(_pending(plan), force=pipeline.force)
        describe_download(plan, pipeline.workers, console)
        describe_coverage(backlog, pipeline.workers, console)
        with (
            ProcessPoolExecutor(max_workers=pipeline.workers) as computing,
            ThreadPoolExecutor(max_workers=pipeline.workers) as fetching,
        ):
            futures.extend(
                computing.submit(compute_coverage, job) for job in backlog.jobs
            )
            stream = _submitting(
                _collecting(
                    run(
                        plan.jobs,
                        lambda job: download_set(job, client, download.loc),
                        fetching,
                    ),
                    fetched,
                ),
                computing,
                futures,
                force=pipeline.force,
            )
            with closing(stream) as events:
                progress.render(events, len(plan.jobs), "download", console)
            if futures:
                progress.render(_drain(futures), len(futures), "coverage", console)
    summary = DownloadSummary(
        ran=sum(1 for outcome in fetched if not outcome.failed),
        failed=sum(1 for outcome in fetched if outcome.failed),
        elapsed=time.monotonic() - started_at,
    )
    return summary, [future.result() for future in futures]


def discard_metadata(outcomes: Sequence[CoverageOutcome]) -> int:
    """Delete the metadata of every set whose coverage is now on disk.

    A set is only discarded once its summary exists, so a run that stopped part
    way never leaves an artifact without the metadata that produced it.

    Args:
        outcomes: Every finished coverage job.

    Returns:
        How many metadata files were removed.
    """
    removed = 0
    for outcome in outcomes:
        if not outcome.failed and outcome.job.summary_path.exists():
            outcome.job.source.unlink(missing_ok=True)
            removed += 1
    return removed


def reindex() -> int:
    """Rebuild the per-feature and catalogue-wide summaries from disk.

    Every feature holding a finished set is gathered, not only the features
    this run computed, so an index a stopped run left short of what is on disk
    is filled in by the next run rather than staying short of it.

    Returns:
        How many summary rows the catalogue index holds.
    """
    for feature_dir in sorted(configs.COVERAGE_ROOT.glob("*/*")):
        catalog.finalise_feature(feature_dir)
    return catalog.rebuild(configs.ARTIFACTS_ROOT, configs.COVERAGE_ROOT)


def totals(outcomes: Sequence[CoverageOutcome], elapsed: float) -> CoverageSummary:
    """Total up what the coverage half of the run did.

    Args:
        outcomes: Every finished coverage job.
        elapsed: How long the run took in seconds.

    Returns:
        The summary.
    """
    return CoverageSummary(
        computed=sum(1 for o in outcomes if not o.failed and not o.empty),
        empty=sum(1 for o in outcomes if not o.failed and o.empty),
        failed=sum(1 for o in outcomes if o.failed),
        events=sum(o.events for o in outcomes if not o.failed),
        discarded=sum(o.discarded for o in outcomes),
        elapsed=elapsed,
    )

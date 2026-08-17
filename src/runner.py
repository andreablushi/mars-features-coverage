"""Running the pipeline's work: one pooled runner, and the two halves it drives."""

from __future__ import annotations

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

from rich.console import Console

from analysis import planner as coverage_planner
from analysis.tasks import run_job as compute_coverage
from cli import progress
from cli.console import describe_coverage, describe_download
from download import planner as download_planner
from download.api import catalog as ode_catalog
from download.api.client import ODEClient
from download.selection.instruments import verify_sets
from download.tasks import run_job as download_set
from models.job import CoverageOutcome, DownloadOutcome, DownloadPlan, Job
from models.progress import Outcome, ProgressEvent
from models.settings import DownloadSettings, PipelineSettings
from storage import layout


def run_jobs(
    jobs: Sequence[Job], execute: Callable[[Job], Outcome], pool: Executor
) -> Iterator[ProgressEvent]:
    """Run every job on the pool, yielding progress as each one finishes.

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


def _measuring(
    events: Iterator[ProgressEvent],
    pool: ProcessPoolExecutor,
    fetched: list[DownloadOutcome],
    started: list[Future[CoverageOutcome]],
    *,
    force: bool,
) -> Iterator[ProgressEvent]:
    """Pass download events through, keeping each one and measuring what landed.

    Args:
        events: The download runner's progress events.
        pool: The process pool the coverage jobs run on.
        fetched: The download outcomes, appended to as they arrive.
        started: The coverage futures, appended to as they are submitted.
        force: Whether to recompute a set that is already done.

    Yields:
        Each event, unchanged.
    """
    for event in events:
        fetched.append(event.outcome)
        if not event.outcome.failed:
            source = event.outcome.job.output_path
            if source.stat().st_size:
                for job in coverage_planner.build_plan([source], force=force).jobs:
                    started.append(pool.submit(compute_coverage, job))
        yield event


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


def run_pipeline(
    download: DownloadSettings, pipeline: PipelineSettings, console: Console
) -> tuple[list[DownloadOutcome], list[CoverageOutcome]]:
    """Download every set still missing and measure every set not yet measured.

    Args:
        download: The settled download choices.
        pipeline: The settled choices for the run as a whole.
        console: The console to render on.

    Returns:
        Every finished download outcome, then every finished coverage outcome.
    """
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
            stream = _measuring(
                run_jobs(
                    plan.jobs,
                    lambda job: download_set(job, client, download.loc),
                    fetching,
                ),
                computing,
                fetched,
                futures,
                force=pipeline.force,
            )
            with closing(stream) as events:
                progress.render(events, len(plan.jobs), "download", console)
            if futures:
                progress.render(
                    (
                        ProgressEvent(completed=done, outcome=future.result())
                        for done, future in enumerate(futures, start=1)
                    ),
                    len(futures),
                    "coverage",
                    console,
                )
    return fetched, [future.result() for future in futures]

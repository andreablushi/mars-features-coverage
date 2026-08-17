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
from analysis.measuring import run_job as compute_coverage
from console import describe_coverage, describe_download, render
from download import planner as download_planner
from download.api.client import ODEClient
from download.fetching import run_job as download_set
from download.selection.instruments import verify_sets
from models.job import Job, Outcome, Plan
from models.progress import ProgressEvent
from models.settings import Settings
from storage import catalog, metadata


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
    fetched: list[Outcome],
    started: list[Future[Outcome]],
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


def _pending(plan: Plan) -> list[Path]:
    """Return the sets already on disk that this run will not download again.

    A set the download is about to rewrite is measured once it lands rather
    than now, so it is left out here and cannot be computed twice.

    Args:
        plan: The download plan, naming every file this run will write.

    Returns:
        The stored metadata files to weigh for the coverage backlog.
    """
    rewriting = {job.output_path for job in plan.jobs}
    return [source for source in metadata.find_sets() if source not in rewriting]


def run_pipeline(
    settings: Settings, console: Console
) -> tuple[list[Outcome], list[Outcome]]:
    """Download every set still missing and measure every set not yet measured.

    Args:
        settings: The settled choices for the run.
        console: The console to render on.

    Returns:
        Every finished download outcome, then every finished coverage outcome.
    """
    futures: list[Future[Outcome]] = []
    fetched: list[Outcome] = []
    with ODEClient() as client:
        refresh = settings.refresh_catalog
        features = catalog.load_features(client, refresh=refresh)
        verify_sets(
            settings.instrument_sets,
            catalog.load_instrument_sets(client, refresh=refresh),
        )
        plan = download_planner.build_plan(
            features,
            settings.instrument_sets,
            names=settings.feature_names,
            force=settings.force,
        )
        backlog = coverage_planner.build_plan(_pending(plan), force=settings.force)
        describe_download(plan, settings.workers, console)
        describe_coverage(backlog, settings.workers, console)
        with (
            ProcessPoolExecutor(max_workers=settings.workers) as computing,
            ThreadPoolExecutor(max_workers=settings.workers) as fetching,
        ):
            futures.extend(
                computing.submit(compute_coverage, job) for job in backlog.jobs
            )
            stream = _measuring(
                run_jobs(
                    plan.jobs,
                    lambda job: download_set(job, client, settings.loc),
                    fetching,
                ),
                computing,
                fetched,
                futures,
                force=settings.force,
            )
            with closing(stream) as events:
                render(events, len(plan.jobs), "download", console)
            if futures:
                render(
                    (
                        ProgressEvent(completed=done, outcome=future.result())
                        for done, future in enumerate(futures, start=1)
                    ),
                    len(futures),
                    "coverage",
                    console,
                )
    return fetched, [future.result() for future in futures]

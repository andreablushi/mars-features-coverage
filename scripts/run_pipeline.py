#!/usr/bin/env python
"""Command line entry point that downloads metadata and computes coverage.

The two stages stay whole and independent; this only overlaps them. A set's
coverage is submitted the moment its download lands, so the computation runs
against everything already on disk while the next download is still in flight.

The saving is bounded by the shorter stage, and downloading is the slower one
by a wide margin, so this buys convenience and fresh artifacts rather than much
time. Run the two scripts separately when only one of them needs redoing.
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Iterator, Sequence
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from contextlib import closing
from pathlib import Path

from rich.console import Console

from analysis import configs as coverage_configs
from analysis import planner as coverage_planner
from analysis.cli import console as coverage_view
from analysis.cli.settings import resolve as resolve_coverage
from analysis.loader import catalog
from analysis.models.job import CoverageJob, JobOutcome
from analysis.models.progress import RunSummary
from analysis.runner import run_job
from common.cli import progress
from common.configs import CONFIG_PATH
from common.models.progress import ProgressEvent
from download import configs as download_configs
from download import planner as download_planner
from download.api import catalog as feature_catalog
from download.api.client import ODEClient
from download.cli import console as download_view
from download.cli.settings import resolve as resolve_download
from download.runner import DownloadRunner


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the combined pipeline.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="run-pipeline",
        description=(
            "Download ODE observation metadata and compute coverage as it "
            "arrives. Every choice not passed here defaults to "
            f"{CONFIG_PATH.name}, in each stage's own section."
        ),
    )
    parser.add_argument(
        "--feature-name",
        nargs="+",
        metavar="NAME",
        help="One or more feature names (default: every feature in the catalog).",
    )
    parser.add_argument(
        "--instrument-set",
        nargs="+",
        metavar="IHID/IID/PT",
        help="One or more instrument sets, such as MRO/CTX/EDR.",
    )
    parser.add_argument(
        "--loc",
        choices=download_configs.LOC_MODES,
        help="How a footprint must relate to the feature box.",
    )
    parser.add_argument(
        "--download-workers", type=int, help="Concurrent downloads to run at once."
    )
    parser.add_argument(
        "--coverage-workers", type=int, help="Concurrent coverage worker processes."
    )
    parser.add_argument(
        "--cumulative-union",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Accumulate the running union of covered ground.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=None,
        help="Redo work already on disk, in both stages.",
    )
    parser.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="Re-fetch the feature and instrument catalogs.",
    )
    return parser


def _pipelined(
    events: Iterator[ProgressEvent],
    pool: ProcessPoolExecutor,
    started: list[Future[JobOutcome]],
    *,
    cumulative_union: bool,
    force: bool,
) -> Iterator[ProgressEvent]:
    """Pass download events through, starting each set's coverage as it lands.

    Args:
        events: The download runner's progress events.
        pool: The process pool the coverage jobs run on.
        started: The coverage futures, appended to as they are submitted.
        cumulative_union: Whether each coverage job keeps the running union.
        force: Whether to recompute a set that is already done.

    Yields:
        Each download event, unchanged.
    """
    for event in events:
        if not event.outcome.failed:
            for job in _coverage_jobs(event.outcome.job.output_path, force=force):
                started.append(pool.submit(run_job, job, cumulative_union))
        yield event


def _coverage_jobs(source: Path, *, force: bool) -> tuple[CoverageJob, ...]:
    """Return the coverage work one downloaded set still needs.

    The planner owns the rule for what counts as already done, so it is asked
    about the single set rather than the rule being repeated here.

    Args:
        source: The JSONL file the download just wrote.
        force: Whether to recompute a set that is already done.

    Returns:
        The set's job, or nothing when it is already computed.
    """
    return coverage_planner.build_plan([source], force=force).jobs


def _finished(started: Sequence[Future[JobOutcome]]) -> Iterator[ProgressEvent]:
    """Yield a progress event as each coverage job finishes.

    Args:
        started: The coverage futures to wait on.

    Yields:
        One event per finished job, in completion order.
    """
    for completed, future in enumerate(as_completed(started), start=1):
        yield ProgressEvent(completed=completed, outcome=future.result())


def _summarise(outcomes: Sequence[JobOutcome], elapsed: float) -> RunSummary:
    """Total up what the coverage half of the run did.

    Args:
        outcomes: Every finished coverage job.
        elapsed: How long the whole run took in seconds.

    Returns:
        The summary, in the shape the coverage console already prints.
    """
    return RunSummary(
        computed=sum(1 for o in outcomes if not o.failed and not o.empty),
        empty=sum(1 for o in outcomes if not o.failed and o.empty),
        failed=sum(1 for o in outcomes if o.failed),
        events=sum(o.events for o in outcomes if not o.failed),
        discarded=sum(o.discarded for o in outcomes),
        elapsed=elapsed,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the download and coverage stages together.

    Args:
        argv: Optional argument list, defaulting to sys.argv.

    Returns:
        A process exit code, non zero when either stage had a failure.
    """
    args = build_parser().parse_args(argv)
    download = resolve_download(
        argparse.Namespace(
            instrument_set=args.instrument_set,
            loc=args.loc,
            workers=args.download_workers,
            force=args.force,
        )
    )
    coverage = resolve_coverage(
        argparse.Namespace(
            cumulative_union=args.cumulative_union,
            workers=args.coverage_workers,
            force=args.force,
        )
    )
    console = Console()
    started_at = time.monotonic()
    outcomes: list[JobOutcome] = []

    with ODEClient() as client:
        features = feature_catalog.load_features(client, refresh=args.refresh_catalog)
        plan = download_planner.build_plan(
            features,
            download.instrument_sets,
            names=args.feature_name,
            force=download.force,
        )
        runner = DownloadRunner(client, workers=download.workers, loc=download.loc)
        download_view.describe_plan(plan, runner.workers, console)
        if not plan.jobs:
            console.print("nothing to do")
            return 0

        with ProcessPoolExecutor(max_workers=coverage.workers) as pool:
            futures: list[Future[JobOutcome]] = []
            with closing(runner.run(plan.jobs)) as events:
                progress.render(
                    _pipelined(
                        events,
                        pool,
                        futures,
                        cumulative_union=coverage.cumulative_union,
                        force=coverage.force,
                    ),
                    len(plan.jobs),
                    "download",
                    console,
                )
            if futures:
                progress.render(_finished(futures), len(futures), "coverage", console)
                outcomes = [future.result() for future in futures]

    for feature_dir in sorted({outcome.job.source.parent for outcome in outcomes}):
        catalog.finalise_feature(coverage_configs.COVERAGE_ROOT, feature_dir)
    indexed = catalog.rebuild(
        coverage_configs.ARTIFACTS_ROOT, coverage_configs.COVERAGE_ROOT
    )

    download_view.print_summary(runner.summary, console)
    summary = _summarise(outcomes, time.monotonic() - started_at)
    coverage_view.print_summary(summary, indexed, (), console)
    return 1 if runner.summary.failed or summary.failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        progress.print_interrupted("jobs")
        raise SystemExit(130) from None

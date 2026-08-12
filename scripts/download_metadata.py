#!/usr/bin/env python
"""Command line entry point for the ODE metadata downloader."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from rich.console import Console

from download import configs, planner
from download.cli import progress as progress_view
from download.cli.args import build_parser
from download.models import DownloadPlan, InstrumentSet
from download.ode import catalog
from download.ode.client import ODEClient
from download.runner import DownloadRunner


def resolve_instrument_sets(args: argparse.Namespace) -> list[InstrumentSet]:
    """Choose the instrument sets to download from the parsed arguments.

    Args:
        args: The parsed command line arguments.

    Returns:
        The instrument sets to use.

    Raises:
        SystemExit: If an --instrument value is not a valid triple.
    """
    if args.instrument:
        try:
            return [InstrumentSet.parse(text) for text in args.instrument]
        except ValueError as exc:
            raise SystemExit(f"error: {exc}") from exc
    source = (
        configs.TEST_INSTRUMENT_SETS if args.test else configs.DEFAULT_INSTRUMENT_SETS
    )
    return [InstrumentSet(*triple) for triple in source]


def resolve_feature_selection(
    args: argparse.Namespace,
) -> tuple[list[str] | None, list[str] | None]:
    """Choose the feature names or classes to download.

    Args:
        args: The parsed command line arguments.

    Returns:
        A pair (names, classes) where at most one is set; both None means all
        features.
    """
    if args.feature_name:
        return list(args.feature_name), None
    if args.feature_class:
        return None, list(args.feature_class)
    if args.test:
        return list(configs.TEST_FEATURE_NAMES), None
    return None, None


def describe_plan(plan: DownloadPlan, workers: int, console: Console) -> None:
    """Print the initial state of the download plan to the console.

    Args:
        plan: The plan produced by the planner.
        workers: The effective worker count.
        console: The console to print on.

    Returns:
        None.
    """
    if plan.degenerate_features:
        console.print(
            f"[yellow]skipping {plan.degenerate_features} degenerate features "
            "(zero-area bbox)[/yellow]"
        )
    console.print(
        f"plan: {plan.feature_count} features x {plan.instrument_set_count} sets, "
        f"{len(plan.jobs)} jobs to run, {plan.skipped_existing} already downloaded, "
        f"{workers} workers"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the metadata download command.

    Args:
        argv: Optional argument list, defaulting to sys.argv.

    Returns:
        A process exit code, non zero when any job failed.
    """
    args = build_parser().parse_args(argv)
    console = Console()
    instrument_sets = resolve_instrument_sets(args)
    names, classes = resolve_feature_selection(args)

    with ODEClient() as client:
        features = catalog.load_features(
            client, args.cache, refresh=args.refresh_catalog
        )
        plan = planner.build_plan(
            features,
            instrument_sets,
            args.out,
            names=names,
            classes=classes,
            force=args.force,
        )
        runner = DownloadRunner(
            client,
            loc=args.loc,
            workers=args.workers,
            min_obs_time=args.min_obs_time,
            max_obs_time=args.max_obs_time,
        )
        describe_plan(plan, runner.workers, console)
        if args.dry_run:
            console.print("dry run: no queries issued")
            return 0
        if not plan.jobs:
            console.print("nothing to do")
            return 0

        events = runner.run(plan.jobs)
        interrupted = False
        try:
            if args.quiet:
                progress_view.consume(events)
            else:
                progress_view.render(events, len(plan.jobs), console)
        except KeyboardInterrupt:
            interrupted = True
            events.close()
            console.print(
                "[yellow]interrupted: pending jobs cancelled, finished files kept. "
                "Re-run to resume.[/yellow]"
            )

    summary = runner.summary
    if summary is None:
        return 130 if interrupted else 0
    progress_view.print_summary(summary, console)
    if interrupted:
        return 130
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

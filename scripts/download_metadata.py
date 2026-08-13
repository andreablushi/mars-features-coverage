#!/usr/bin/env python
"""Command line entry point for the ODE metadata downloader."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import closing

from rich.console import Console

from download import configs, planner
from download.api import catalog
from download.api.client import ODEClient
from download.cli import console as view
from download.cli.args import build_parser
from download.models.instrument import InstrumentSet
from download.runner import DownloadRunner


def main(argv: Sequence[str] | None = None) -> int:
    """Run the metadata download command.

    Args:
        argv: Optional argument list, defaulting to sys.argv.

    Returns:
        A process exit code, non zero when any job failed.
    """
    args = build_parser().parse_args(argv)
    console = Console()
    instrument_sets = [
        InstrumentSet(*triple) for triple in configs.DEFAULT_INSTRUMENT_SETS
    ]

    with ODEClient() as client:
        features = catalog.load_features(client, refresh=args.refresh_catalog)
        plan = planner.build_plan(
            features, instrument_sets, names=args.feature_name, force=args.force
        )
        runner = DownloadRunner(client, workers=args.workers)
        view.describe_plan(plan, runner.workers, console)
        if not plan.jobs:
            console.print("nothing to do")
            return 0

        with closing(runner.run(plan.jobs)) as events:
            view.render(events, len(plan.jobs), console)

    view.print_summary(runner.summary, console)
    return 1 if runner.summary.failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        view.print_interrupted()
        raise SystemExit(130) from None

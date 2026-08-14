#!/usr/bin/env python
"""Command line entry point for the ODE metadata downloader."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import closing

from rich.console import Console

from common.cli import progress
from download import planner
from download.api import catalog
from download.api.client import ODEClient
from download.cli import console as view
from download.cli.args import build_parser
from download.cli.settings import resolve
from download.runner import DownloadRunner


def main(argv: Sequence[str] | None = None) -> int:
    """Run the metadata download command.

    Args:
        argv: Optional argument list, defaulting to sys.argv.

    Returns:
        A process exit code, non zero when any job failed.
    """
    args = build_parser().parse_args(argv)
    settings = resolve(args)
    console = Console()

    with ODEClient() as client:
        features = catalog.load_features(client, refresh=args.refresh_catalog)
        plan = planner.build_plan(
            features,
            settings.instrument_sets,
            names=args.feature_name,
            force=settings.force,
        )
        runner = DownloadRunner(client, workers=settings.workers, loc=settings.loc)
        view.describe_plan(plan, runner.workers, console)
        if not plan.jobs:
            console.print("nothing to do")
            return 0

        with closing(runner.run(plan.jobs)) as events:
            progress.render(events, len(plan.jobs), "download", console)

    view.print_summary(runner.summary, console)
    return 1 if runner.summary.failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        progress.print_interrupted("jobs")
        raise SystemExit(130) from None

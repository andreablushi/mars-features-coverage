#!/usr/bin/env python
"""Command line entry point for the coverage computation stage."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from contextlib import closing

from rich.console import Console

from analysis import configs, runner
from analysis.cli import console as view


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the coverage computation.

    The stage always runs over every downloaded feature, so it takes no
    selection arguments.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="compute-coverage",
        description=(
            "Compute the spatial and temporal coverage of every instrument set "
            "over every downloaded geological feature."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=configs.DEFAULT_WORKERS,
        help="Concurrent worker processes.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the coverage computation command.

    Args:
        argv: Optional argument list, defaulting to sys.argv.

    Returns:
        A process exit code, non zero when any feature failed.
    """
    args = build_parser().parse_args(argv)
    console = Console()
    directories = runner.discover()

    coverage_runner = runner.CoverageRunner(workers=args.workers)
    view.describe_plan(len(directories), coverage_runner.workers, console)
    if not directories:
        console.print("nothing to do")
        return 0

    with closing(coverage_runner.run(directories)) as events:
        view.render(events, len(directories), console)

    view.print_summary(coverage_runner.summary, console)
    return 1 if coverage_runner.summary.failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        view.print_interrupted()
        raise SystemExit(130) from None

#!/usr/bin/env python
"""Command line entry point for the feature coverage survey."""

from __future__ import annotations

import time

from rich.console import Console

import runner
import settings
from analysis import planner as coverage_planner
from cli import progress
from cli.console import print_summary
from storage import layout


def main() -> int:
    """Download ODE metadata for geological features and measure their coverage.

    Every choice a run makes is read from the config file.

    Returns:
        A process exit code, non zero when either half had a failure.
    """
    choices = settings.pipeline()
    console = Console()
    started_at = time.monotonic()

    downloaded, outcomes = runner.survey(settings.download(), choices, console)

    if not choices.keep_metadata:
        removed = runner.discard_metadata(outcomes)
        if removed:
            console.print(f"discarded metadata for {removed} computed sets")

    totals = runner.totals(outcomes, time.monotonic() - started_at)
    print_summary(
        downloaded,
        totals,
        runner.reindex(),
        coverage_planner.unfinished(layout.find_sets()),
        console,
    )
    return 1 if totals.failed or downloaded.failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        progress.print_interrupted("jobs")
        raise SystemExit(130) from None

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

    Every choice a run makes is read from the config file, so the same file
    describes what was run and what to run again. There is nothing to pass
    here, and nothing a flag could quietly change between two runs.

    Returns:
        A process exit code, non zero when either half had a failure.
    """
    choices = settings.pipeline()
    coverage = settings.coverage()
    console = Console()
    started_at = time.monotonic()

    if choices.coverage_only:
        downloaded, outcomes = None, runner.compute_only(coverage, console)
    else:
        downloaded, outcomes = runner.download_and_compute(
            settings.download(), coverage, choices, console
        )

    if not choices.keep_metadata:
        removed = runner.discard_metadata(outcomes)
        if removed:
            console.print(f"discarded metadata for {removed} computed sets")

    totals = runner.totals(outcomes, time.monotonic() - started_at)
    print_summary(
        downloaded,
        totals,
        runner.reindex(outcomes),
        coverage_planner.unfinished(layout.find_sets()),
        console,
    )
    return 1 if totals.failed or (downloaded and downloaded.failed) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        progress.print_interrupted("jobs")
        raise SystemExit(130) from None

#!/usr/bin/env python
"""Command line entry point for the feature coverage survey."""

from __future__ import annotations

import time

from rich.console import Console

import analysis.utils.settings as settings
from analysis import planner, runner
from analysis.console import print_interrupted, print_summary
from analysis.coverage import summary
from analysis.metadata import file_explorer
from analysis.models.progress import CoverageSummary, DownloadSummary


def main() -> int:
    """Download ODE metadata for geological features and measure their coverage.

    Returns:
        A process exit code, non zero when either half had a failure.
    """
    choices = settings.load()
    console = Console()
    started_at = time.monotonic()

    fetched, outcomes = runner.run_pipeline(choices, console)

    if not choices.keep_metadata:
        removed = file_explorer.discard_metadata(outcomes)
        if removed:
            console.print(f"discarded metadata for {removed} computed sets")

    elapsed = time.monotonic() - started_at
    downloaded = DownloadSummary.from_outcomes(fetched, elapsed)
    computed = CoverageSummary.from_outcomes(outcomes, elapsed)
    print_summary(
        downloaded,
        computed,
        summary.reindex(),
        planner.unfinished(file_explorer.find_sets()),
        console,
    )
    return 1 if computed.failed or downloaded.failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print_interrupted("jobs")
        raise SystemExit(130) from None

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
from models.progress import CoverageSummary, DownloadSummary
from storage import catalog, layout


def main() -> int:
    """Download ODE metadata for geological features and measure their coverage.

    Every choice a run makes is read from the config file.

    Returns:
        A process exit code, non zero when either half had a failure.
    """
    download, choices = settings.load()
    console = Console()
    started_at = time.monotonic()

    fetched, outcomes = runner.run_pipeline(download, choices, console)

    if not choices.keep_metadata:
        removed = layout.discard_metadata(outcomes)
        if removed:
            console.print(f"discarded metadata for {removed} computed sets")

    elapsed = time.monotonic() - started_at
    downloaded = DownloadSummary.of(fetched, elapsed)
    computed = CoverageSummary.of(outcomes, elapsed)
    print_summary(
        downloaded,
        computed,
        catalog.reindex(),
        coverage_planner.unfinished(layout.find_sets()),
        console,
    )
    return 1 if computed.failed or downloaded.failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        progress.print_interrupted("jobs")
        raise SystemExit(130) from None

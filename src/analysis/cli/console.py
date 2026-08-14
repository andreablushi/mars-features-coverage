"""Console output for a coverage run: plan and totals."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rich.console import Console

from analysis.configs import MISSING_SHOWN
from analysis.models.job import CoveragePlan
from analysis.models.progress import RunSummary


def describe_plan(
    plan: CoveragePlan, workers: int, console: Console | None = None
) -> None:
    """Print the initial state of the coverage plan.

    Args:
        plan: The plan produced by the planner.
        workers: The effective worker count.
        console: Optional console to print on.

    Returns:
        None.
    """
    console = console or Console()
    console.print(
        f"plan: {plan.feature_count} features, {plan.set_count} instrument sets, "
        f"{len(plan.jobs)} to compute, {plan.skipped_existing} already done, "
        f"{workers} workers"
    )


def print_summary(
    summary: RunSummary,
    indexed: int,
    missing: Sequence[Path] = (),
    console: Console | None = None,
) -> None:
    """Print the totals for a finished run.

    Args:
        summary: The summary produced by the runner.
        indexed: Summary rows gathered into the catalogue index.
        missing: The instrument sets that still have no artifact on disk.
        console: Optional console to print on.

    Returns:
        None.
    """
    console = console or Console()
    console.print(
        f"done in {summary.elapsed:.1f}s: {summary.computed} sets, "
        f"{summary.events:,} observation rows, {summary.failed} failed, "
        f"{indexed:,} rows indexed"
    )
    if summary.empty or summary.discarded:
        console.print(
            f"[yellow]{summary.empty} sets measured nothing, "
            f"{summary.discarded:,} records discarded for no footprint, "
            f"no start time, or no overlap[/yellow]"
        )
    _print_missing(missing, console)


def _print_missing(missing: Sequence[Path], console: Console) -> None:
    """Name the instrument sets left with no artifact once the run is over.

    Both indexes are rebuilt from whatever finished, so without this a gap in
    the catalogue reads as a feature nothing ever observed.

    Args:
        missing: The instrument set metadata files with no artifact.
        console: The console to print on.

    Returns:
        None.
    """
    if not missing:
        return
    console.print(f"[yellow]{len(missing)} sets still have no artifact:[/yellow]")
    for source in missing[:MISSING_SHOWN]:
        console.print(f"[yellow]  {source}[/yellow]")
    if len(missing) > MISSING_SHOWN:
        console.print(f"[yellow]  and {len(missing) - MISSING_SHOWN} more[/yellow]")

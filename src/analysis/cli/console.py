"""Console output for a coverage run: plan and totals."""

from __future__ import annotations

from rich.console import Console

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
    summary: RunSummary, indexed: int, console: Console | None = None
) -> None:
    """Print the totals for a finished run.

    Args:
        summary: The summary produced by the runner.
        indexed: Summary rows gathered into the catalogue index.
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
            f"{summary.discarded:,} records discarded for no footprint "
            f"or no start time[/yellow]"
        )

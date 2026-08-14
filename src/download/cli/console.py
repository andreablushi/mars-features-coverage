"""Console output for a download run: plan and totals."""

from __future__ import annotations

from rich.console import Console

from download.models.job import DownloadPlan
from download.models.progress import RunSummary


def describe_plan(
    plan: DownloadPlan, workers: int, console: Console | None = None
) -> None:
    """Print the initial state of the download plan.

    Args:
        plan: The plan produced by the planner.
        workers: The effective worker count.
        console: Optional console to print on.

    Returns:
        None.
    """
    console = console or Console()
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


def print_summary(summary: RunSummary, console: Console | None = None) -> None:
    """Print the totals for a finished run.

    Args:
        summary: The summary produced by the runner.
        console: Optional console to print on.

    Returns:
        None.
    """
    console = console or Console()
    console.print(
        f"done in {summary.elapsed:.1f}s: {summary.ran} jobs, {summary.failed} failed"
    )

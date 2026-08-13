"""Console output for a coverage run: plan, progress, and totals."""

from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TimeRemainingColumn

from analysis.models import ProgressEvent, RunSummary


def describe_plan(features: int, workers: int, console: Console | None = None) -> None:
    """Print what the run is about to do.

    Args:
        features: How many feature directories were discovered.
        workers: The effective worker count.
        console: Optional console to print on.

    Returns:
        None.
    """
    console = console or Console()
    console.print(f"plan: {features} features, {workers} workers")


def render(
    events: Iterable[ProgressEvent], total: int, console: Console | None = None
) -> None:
    """Draw a live progress bar while consuming runner events.

    Shows the bar, the completed and total feature counts, and the estimated
    time remaining. Failures are printed above the bar as they happen.

    Args:
        events: The progress events produced by the runner.
        total: The number of features in the run.
        console: Optional console to render on.

    Returns:
        None.
    """
    console = console or Console()
    with Progress(
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        TimeRemainingColumn(compact=True),
        console=console,
    ) as progress:
        task = progress.add_task("coverage", total=total)
        for event in events:
            if event.outcome.failed:
                console.print(
                    f"[red]error[/red] {event.outcome.label}: {event.outcome.error}"
                )
            progress.update(task, completed=event.completed)


def print_interrupted(console: Console | None = None) -> None:
    """Print the notice shown when the run is stopped with Ctrl-C.

    Args:
        console: Optional console to print on.

    Returns:
        None.
    """
    console = console or Console()
    console.print(
        "[yellow]interrupted: pending features cancelled, finished files kept. "
        "Re-run to recompute.[/yellow]"
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
    if summary.degenerate:
        console.print(
            f"[yellow]{summary.degenerate} features had a zero-area bounding box "
            "and were recorded without coverage[/yellow]"
        )
    console.print(
        f"done in {summary.elapsed:.1f}s: {summary.features} features, "
        f"{summary.events:,} observation rows, {summary.failed} failed"
    )

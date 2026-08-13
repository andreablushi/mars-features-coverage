"""Rendering of runner progress events for the terminal."""

from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TimeRemainingColumn

from download.models import ProgressEvent, RunSummary


def render(
    events: Iterable[ProgressEvent], total: int, console: Console | None = None
) -> None:
    """Draw a live progress bar while consuming runner events.

    Shows the bar, the completed and total job counts, and the estimated time
    remaining. Failures are printed above the bar as they happen.

    Args:
        events: The progress events produced by the runner.
        total: The number of jobs in the run.
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
        task = progress.add_task("download", total=total)
        for event in events:
            if event.outcome.failed:
                console.print(
                    f"[red]error[/red] {event.outcome.job.label}: {event.outcome.error}"
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
        "[yellow]interrupted: pending jobs cancelled, finished files kept. "
        "Re-run to resume.[/yellow]"
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

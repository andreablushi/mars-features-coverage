"""Rendering of runner progress events for the terminal."""

from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from download.models import ProgressEvent, RunSummary

_LABEL_WIDTH = 30


def _truncate(text: str, width: int = _LABEL_WIDTH) -> str:
    """Shorten text to a fixed width so the progress line does not jitter.

    Args:
        text: The text to shorten.
        width: The maximum number of characters.

    Returns:
        The text, truncated with an ellipsis when too long.
    """
    if len(text) <= width:
        return text.ljust(width)
    return text[: width - 1] + "…"


def render(
    events: Iterable[ProgressEvent], total: int, console: Console | None = None
) -> None:
    """Draw a live progress bar while consuming runner events.

    Shows the percentage, the completed and total job counts, elapsed and
    remaining time, the job currently finishing, and running row and failure
    totals. Failures are printed above the bar as they happen.

    Args:
        events: The progress events produced by the runner.
        total: The number of jobs in the run.
        console: Optional console to render on.

    Returns:
        None.
    """
    console = console or Console()
    columns = (
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[label]}"),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
        MofNCompleteColumn(),
        TimeRemainingColumn(compact=True),
        TextColumn("{task.fields[stats]}"),
    )
    with Progress(*columns, console=console) as progress:
        task = progress.add_task(
            "download",
            total=total,
            label=_truncate("starting"),
            stats="",
        )
        for event in events:
            if event.outcome.failed:
                console.print(
                    f"[red]error[/red] {event.outcome.job.label}: {event.outcome.error}"
                )
            failures = f" [red]{event.failed} failed[/red]" if event.failed else ""
            progress.update(
                task,
                completed=event.completed,
                label=_truncate(event.outcome.job.label),
                stats=f"{event.rows:,} rows{failures}",
            )


def consume(events: Iterable[ProgressEvent]) -> None:
    """Consume runner events without rendering anything.

    Args:
        events: The progress events produced by the runner.

    Returns:
        None.
    """
    for _ in events:
        pass


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
        f"done in {summary.elapsed:.1f}s: {summary.ran} jobs, "
        f"{summary.rows:,} rows, {summary.empty} empty, {summary.failed} failed"
    )

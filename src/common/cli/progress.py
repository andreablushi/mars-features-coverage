"""The live progress bar both pipelines draw while a run is in flight."""

from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress

from common.models.progress import ProgressEvent


def render(
    events: Iterable[ProgressEvent],
    total: int,
    description: str,
    console: Console | None = None,
) -> None:
    """Draw a live progress bar while consuming runner events.

    Shows the bar and the completed and total counts. Failures are printed
    above the bar as they happen.

    Args:
        events: The progress events produced by a runner.
        total: The number of units in the run.
        description: The label for the progress task.
        console: Optional console to render on.

    Returns:
        None.
    """
    console = console or Console()
    with Progress(
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(description, total=total)
        for event in events:
            if event.outcome.failed:
                console.print(
                    f"[red]error[/red] {event.outcome.label}: {event.outcome.error}"
                )
            progress.update(task, completed=event.completed)


def print_interrupted(noun: str, console: Console | None = None) -> None:
    """Print the notice shown when a run is stopped with Ctrl-C.

    Args:
        noun: What was left pending, for example "features" or "jobs".
        console: Optional console to print on.

    Returns:
        None.
    """
    console = console or Console()
    console.print(
        f"[yellow]interrupted: pending {noun} cancelled, finished files kept. "
        "Re-run to resume.[/yellow]"
    )

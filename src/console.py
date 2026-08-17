"""Everything the pipeline prints: plans, live progress, and totals."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress

from models.job import Plan
from models.progress import CoverageSummary, DownloadSummary, ProgressEvent

# How many items are named before the rest are counted
LISTED = 5


def describe_download(plan: Plan, workers: int, console: Console) -> None:
    """Print the initial state of the download plan.

    Args:
        plan: The plan produced by the download planner.
        workers: The effective worker count.
        console: The console to print on.

    Returns:
        None.
    """
    if plan.sizeless_features:
        shown = ", ".join(plan.sizeless_features[:LISTED])
        rest = len(plan.sizeless_features) - LISTED
        console.print(
            f"[yellow]{len(plan.sizeless_features)} features carry no extent in "
            f"the catalogue and were not queried: {shown}"
            f"{f', and {rest} more' if rest > 0 else ''}[/yellow]"
        )
    console.print(
        f"download: {plan.feature_count} features x {plan.set_count} sets, "
        f"{len(plan.jobs)} to run, {plan.skipped_existing} already downloaded, "
        f"{workers} workers"
    )


def describe_coverage(plan: Plan, workers: int, console: Console) -> None:
    """Print the initial state of the coverage plan.

    Args:
        plan: The plan produced by the coverage planner.
        workers: The effective worker count.
        console: The console to print on.

    Returns:
        None.
    """
    console.print(
        f"coverage: {plan.feature_count} features, {plan.set_count} instrument sets, "
        f"{len(plan.jobs)} to compute, {plan.skipped_existing} already done, "
        f"{workers} workers"
    )


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


def print_summary(
    download: DownloadSummary,
    coverage: CoverageSummary,
    indexed: int,
    missing: Sequence[Path],
    console: Console,
) -> None:
    """Print the totals for a finished run.

    Args:
        download: The download half's totals.
        coverage: The coverage half's totals.
        indexed: Summary rows gathered into the catalogue index.
        missing: The instrument sets that still have no artifact on disk.
        console: The console to print on.

    Returns:
        None.
    """
    console.print(
        f"downloaded {download.ran} sets, {download.failed} failed, "
        f"in {download.elapsed:.1f}s"
    )
    console.print(
        f"computed {coverage.computed} sets, {coverage.events:,} observation rows, "
        f"{coverage.failed} failed, {indexed:,} rows indexed, "
        f"in {coverage.elapsed:.1f}s"
    )
    if coverage.empty or coverage.discarded:
        console.print(
            f"[yellow]{coverage.empty} sets measured nothing, "
            f"{coverage.discarded:,} records discarded for no footprint, "
            f"no start time, or no overlap[/yellow]"
        )
    if not missing:
        return
    console.print(f"[yellow]{len(missing)} sets still have no artifact:[/yellow]")
    for source in missing[:LISTED]:
        console.print(f"[yellow]  {source}[/yellow]")
    if len(missing) > LISTED:
        console.print(f"[yellow]  and {len(missing) - LISTED} more[/yellow]")

"""Everything the pipeline prints: plans, live progress, and totals."""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress

from models.job import Plan
from models.progress import CoverageSummary, DownloadSummary, ProgressEvent

# How many items are named before the rest are counted
LISTED = 5

# Set by a platform run, whose log takes plain flushed lines rather than a bar.
PLAIN_LOG_ENV = "PIPELINE_PLAIN_LOG"

# How many progress lines a stage prints where no cursor can be moved
LOGGED_LINES = 50


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

    A run that set PLAIN_LOG_ENV takes named lines instead, since a live bar
    leaves a captured log looking stalled from the first job to the last.

    Args:
        events: The progress events produced by a runner.
        total: The number of units in the run.
        description: The label for the progress task.
        console: Optional console to render on.

    Returns:
        None.
    """
    console = console or Console()
    if os.environ.get(PLAIN_LOG_ENV):
        _log(events, total, description)
        return
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


def _log(events: Iterable[ProgressEvent], total: int, description: str) -> None:
    """Print which job a stage has reached, every so many jobs.

    Written with the plain flushed print the platform's log carries, since the
    console's own writes are buffered there and surface only once at the end.

    Args:
        events: The progress events produced by a runner.
        total: The number of units in the run.
        description: The label for the stage.

    Returns:
        None.
    """
    step = max(1, total // LOGGED_LINES)
    for event in events:
        outcome = event.outcome
        if outcome.failed:
            print(f"error {outcome.label}: {outcome.error}", flush=True)
        if event.completed % step == 0 or event.completed == total:
            share = event.completed / total
            print(
                f"{description} {event.completed}/{total} ({share:.0%}) "
                f"{outcome.label}",
                flush=True,
            )


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

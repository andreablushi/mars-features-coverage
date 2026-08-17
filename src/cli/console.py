"""Everything the pipeline prints: plans, totals, and what was left undone."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rich.console import Console

from models.job import CoveragePlan, DownloadPlan
from models.progress import CoverageSummary, DownloadSummary

# How many items are named before the rest are counted
LISTED = 5


def describe_download(plan: DownloadPlan, workers: int, console: Console) -> None:
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
        f"download: {plan.feature_count} features x {plan.instrument_set_count} sets, "
        f"{len(plan.jobs)} to run, {plan.skipped_existing} already downloaded, "
        f"{workers} workers"
    )


def describe_coverage(plan: CoveragePlan, workers: int, console: Console) -> None:
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

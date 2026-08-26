"""How big a dataset each strategy would leave, and how good its tiles are."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from prediction.models.dataset import DatasetStats
from visualization.common import tables, wording
from visualization.common.tables import Row

_HEADINGS = ("Strategy", "Tiles searched", "Tiles kept", "Share kept")


def final(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate the dataset each strategy would leave behind.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "The dataset each strategy would leave",
        _HEADINGS,
        [_row(stats) for stats in read.values()],
    )


def _kept(kept: int, searched: int) -> str:
    """Say what share of the tiles searched were kept rather than refused.

    Args:
        kept: How many earned a window worth keeping.
        searched: How many the search ran over.

    Returns:
        The share, or nothing at all when no tile was searched.
    """
    if not searched:
        return wording.NOTHING
    return f"{kept / searched:.1%}"


def _row(stats: DatasetStats) -> Row:
    """Write one strategy's row.

    Args:
        stats: What it made of the features swept.

    Returns:
        The row.
    """
    held = stats.held
    return (
        stats.strategy,
        f"{held.searched:,}",
        f"{held.kept:,}",
        _kept(held.kept, held.searched),
    )

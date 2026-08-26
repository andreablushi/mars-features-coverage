"""How big a dataset each strategy would leave, and how good its tiles are."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from prediction.stats.dataset import DatasetStats
from visualization.common import tables, wording
from visualization.common.tables import Row

_HEADINGS = ("Strategy", "Tiles searched", "Tiles kept", "Ground kept")


def final(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate the dataset each strategy would leave behind.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    if not read:
        return tables.written("The dataset each strategy would leave", _HEADINGS, [])
    first = next(iter(read.values()))
    headings = (
        _HEADINGS
        + tuple(_holding(counted) for counted in first.reaching)
        + tuple(f"{band:.0%} shared" for band in first.covered)
    )
    return tables.written(
        "The dataset each strategy would leave",
        headings,
        [_row(stats) for stats in read.values()],
    )


def _holding(counted: int) -> str:
    """Name the column counting the tiles holding so many instruments.

    Args:
        counted: How many instruments a tile has to hold.

    Returns:
        The heading.
    """
    return "1 instrument" if counted == 1 else f"{counted} instruments"


def _row(stats: DatasetStats) -> Row:
    """Write one strategy's row.

    Args:
        stats: What it made of the features swept.

    Returns:
        The row.
    """
    held = stats.held
    return (
        (
            stats.strategy,
            f"{held.searched:,}",
            f"{held.kept:,}",
            wording.ground(held.kept_km2, held.area_km2),
        )
        + tuple(f"{tiles:,}" for tiles in stats.reaching.values())
        + tuple(f"{tiles:,}" for tiles in stats.covered.values())
    )

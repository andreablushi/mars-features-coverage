"""How each strategy cuts the features up, and what lands on the tiles."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from prediction.models.dataset import DatasetStats
from survey import strategies
from utils.maths import quantities
from visualization.common import tables
from visualization.common.tables import Row

_TITLE = "How big a tile is and what lands on it"
_TILES = (
    "Strategy",
    "Tile width asked",
    "Tiles searched",
    "Mean tile",
    "Spread",
    "Smallest",
    "Largest",
)


def sizes(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how big a tile each strategy cuts into and what it holds.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    if not read:
        return tables.written(_TITLE, _TILES, [])
    first = next(iter(read.values()))
    headings = _TILES + tuple(
        heading
        for iid in first.iids
        for heading in (f"{iid} mean observations", f"{iid} spread")
    )
    return tables.written(_TITLE, headings, [_row(stats) for stats in read.values()])


def _row(stats: DatasetStats) -> Row:
    """Write one strategy's row, its tiles first and each instrument after.

    Args:
        stats: What the strategy made of the features swept.

    Returns:
        The row.
    """
    cut = stats.sizes
    return (
        stats.strategy,
        f"{strategies.named(stats.strategy).tile_km:,.0f} km",
        f"{cut.counted:,}",
        quantities.area(cut.mean),
        f"± {quantities.area(cut.deviation)}",
        quantities.area(cut.low),
        quantities.area(cut.high),
    ) + tuple(
        cell
        for iid in stats.iids
        for cell in (
            f"{stats.offered[iid].mean:,.1f}",
            f"± {stats.offered[iid].deviation:,.1f}",
        )
    )

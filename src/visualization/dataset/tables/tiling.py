"""How each strategy cuts the features up, and what lands on the tiles."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from prediction.stats.dataset import DatasetStats
from survey import strategies
from utils.maths import quantities
from visualization.common import tables
from visualization.common.tables import Row

_TILES = (
    "Strategy",
    "Tile width asked",
    "Tiles searched",
    "Mean tile",
    "Spread",
    "Smallest",
    "Largest",
)
_OFFERED = (
    "Strategy",
    "Instrument",
    "Mean of a tile",
    "Spread",
    "Most on one tile",
)
_NOTE = (
    "A tile is a square of the feature's grid, so a tile at the edge of the "
    "grid holds less of the feature than one in the middle."
)


def sizes(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how big a tile each strategy cuts the features into.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How big a tile is",
        _TILES,
        [
            (
                stats.strategy,
                f"{strategies.named(stats.strategy).tile_km:,.0f} km",
                f"{stats.sizes.counted:,}",
                quantities.area(stats.sizes.mean),
                f"± {quantities.area(stats.sizes.deviation)}",
                quantities.area(stats.sizes.low),
                quantities.area(stats.sizes.high),
            )
            for stats in read.values()
        ],
        note=_NOTE,
    )


def offered(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how many observations a tile holds, instrument by instrument.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How many observations a tile holds",
        _OFFERED,
        [_landed(stats, iid) for stats in read.values() for iid in stats.iids],
        lead="every observation the tile admits, before a window is searched over it",
    )


def _landed(stats: DatasetStats, iid: str) -> Row:
    """Write one instrument's row under one strategy.

    Args:
        stats: What the strategy made of the features swept.
        iid: The instrument the row describes.

    Returns:
        The row.
    """
    counted = stats.offered[iid]
    return (
        stats.strategy,
        iid,
        f"{counted.mean:,.1f}",
        f"± {counted.deviation:,.1f}",
        f"{counted.high:,.0f}",
    )

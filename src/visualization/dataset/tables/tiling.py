"""How each strategy cuts the features up, and what lands on the tiles."""

from __future__ import annotations

import math
from collections.abc import Mapping

import ipywidgets as widgets

from coverage import configs
from sampling.models.dataset import DatasetStats
from sampling.models.spread import Spread
from selector import strategies
from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row

# The instrument whose pixels are radargram columns rather than picture elements.
SOUNDER = "SHARAD"

# The track one of its columns covers, in kilometres.
_COLUMN_KM = configs.SHARAD_ALONG_TRACK_M / 1000.0

# How much further a corner to corner crossing runs than a straight one.
_DIAGONAL = math.sqrt(2.0)

_TITLE = "How big a tile is and what lands on it"
_TILES = (
    "Strategy",
    "Tile width asked",
    "Tiles searched",
    "Mean tile",
    "Spread",
    "Smallest",
    "Largest",
    "Tile across",
    f"{SOUNDER} across",
    f"{SOUNDER} corner to corner",
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
        for heading in (
            f"{iid} mean observations",
            f"{iid} spread",
            f"{iid} a full tile",
            f"{iid} all passes",
            f"{iid} asked",
        )
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
    across = math.sqrt(cut.mean) if cut.mean > 0.0 else 0.0
    return (
        stats.strategy,
        f"{strategies.named(stats.strategy).tile_km:,.0f} km",
        f"{cut.counted:,}",
        quantities.area(cut.mean),
        f"± {quantities.area(cut.deviation)}",
        quantities.area(cut.low),
        quantities.area(cut.high),
        f"{across:,.0f} km",
        _columns(across),
        _columns(across * _DIAGONAL),
    ) + tuple(cell for iid in stats.iids for cell in _instrument(stats, iid, cut.mean))


def _instrument(stats: DatasetStats, iid: str, tile_km2: float) -> tuple[str, ...]:
    """Write what one instrument offers a tile and what the strategy asks of it.

    Args:
        stats: What the strategy made of the features swept.
        iid: The instrument to write.
        tile_km2: How much ground the mean tile holds.

    Returns:
        Its observations, what a tile-filling look would land, and the bar it clears.
    """
    held = stats.held
    landed = held.landed.get(iid)
    asked = strategies.named(stats.strategy).admits.get(iid)
    return (
        f"{stats.offered[iid].mean:,.1f}",
        f"± {stats.offered[iid].deviation:,.1f}",
        _fills(held.pixel_km2.get(iid), tile_km2),
        _measured(landed, iid),
        f"{asked:,.0f}" if asked else wording.NOTHING,
    )


def _fills(pixel_km2: Spread | None, tile_km2: float) -> str:
    """Write how many pixels a look covering the whole tile would land.

    Args:
        pixel_km2: The ground one of its pixels covers, tile by tile, or None.
        tile_km2: How much ground the mean tile holds.

    Returns:
        The pixels it would land there, and nothing where no pixel size is known.
    """
    if pixel_km2 is None or not pixel_km2.counted or not pixel_km2.mean:
        return wording.UNCOUNTED
    return quantities.compact(tile_km2 / pixel_km2.mean)


def _measured(landed: Spread | None, iid: str) -> str:
    """Write what an instrument really landed on a tile, in its own units.

    Args:
        landed: The pixels it lands on a tile, tile by tile, or None.
        iid: The instrument, which says whether its pixels are columns.

    Returns:
        The measurement, as columns for a sounder and as pixels for an imager.
    """
    if landed is None:
        return wording.UNCOUNTED
    return wording.columns(landed) if iid == SOUNDER else wording.landed(landed)


def _columns(track_km: float) -> str:
    """Write how many radargram columns a stretch of track comes to.

    Args:
        track_km: How far the sounder reaches, in kilometres.

    Returns:
        The columns it lays down there, and nothing where it reaches no ground.
    """
    if track_km <= 0.0:
        return wording.NOTHING
    return f"{track_km / _COLUMN_KM:,.0f}"

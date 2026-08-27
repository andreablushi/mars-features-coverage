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

# The track one of the sounder's columns covers, in kilometres.
_COLUMN_KM = configs.SHARAD_ALONG_TRACK_M / 1000.0

# How much further a corner to corner crossing runs than a straight one.
_DIAGONAL = math.sqrt(2.0)

_SIZES_TITLE = "How big a tile is"
_TILES = (
    "Strategy",
    "Tile width asked",
    "Tiles searched",
    "Mean tile",
    "Spread",
    "Smallest",
    "Largest",
    "Tile across",
    f"{wording.SOUNDER} pixels across",
    f"{wording.SOUNDER} pixels corner to corner",
)

_LANDED_TITLE = "What each instrument lands on a tile"
_LANDED = (
    "Strategy",
    "Instrument",
    "Mean observations",
    "Spread",
    "Mean pixels landed",
    "Pixels asked",
)


def sizes(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how big a tile each strategy cuts into and what fills one.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    if not read:
        return tables.written(_SIZES_TITLE, _TILES, [])
    first = next(iter(read.values()))
    headings = _TILES + tuple(f"{iid} pixels to fill a tile" for iid in first.iids)
    return tables.written(
        _SIZES_TITLE, headings, [_row(stats) for stats in read.values()]
    )


def landed(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate what each instrument really lands on a tile and what is asked of it.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    rows: list[Row] = []
    # Every strategy after the first is ruled off from the one above it
    groups: list[int] = []
    for stats in read.values():
        if rows:
            groups.append(len(rows))
        rows.extend(_landing(stats))
    return tables.written(_LANDED_TITLE, _LANDED, rows, groups=groups)


def _row(stats: DatasetStats) -> Row:
    """Write one strategy's row, its tiles first and what fills one after.

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
    ) + tuple(_fills(stats.held.pixel_km2.get(iid), cut.mean) for iid in stats.iids)


def _landing(stats: DatasetStats) -> list[Row]:
    """Write one strategy's rows, an instrument each.

    Args:
        stats: What the strategy made of the features swept.

    Returns:
        The rows, in the order the instruments are drawn.
    """
    return [_lands(stats, iid) for iid in stats.iids]


def _lands(stats: DatasetStats, iid: str) -> Row:
    """Write what one instrument offers a tile and what the strategy asks of it.

    Args:
        stats: What the strategy made of the features swept.
        iid: The instrument to write.

    Returns:
        Its observations, the pixels it lands, and the bar it clears.
    """
    offered = stats.offered[iid]
    asked = strategies.named(stats.strategy).admits.get(iid)
    return (
        stats.strategy,
        iid,
        f"{offered.mean:,.1f}",
        f"± {offered.deviation:,.1f}",
        _measured(stats.held.landed.get(iid), iid),
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


def _measured(pixels: Spread | None, iid: str) -> str:
    """Write what an instrument really landed on a tile, in its own units.

    Args:
        pixels: The pixels it lands on a tile, tile by tile, or None.
        iid: The instrument, which says whether its pixels are columns.

    Returns:
        The measurement, as columns for a sounder and as pixels for an imager.
    """
    if pixels is None:
        return wording.UNCOUNTED
    return wording.columns(pixels) if iid == wording.SOUNDER else wording.landed(pixels)


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

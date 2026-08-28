"""How each strategy cuts the features up, and what lands on the tiles."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping

import ipywidgets as widgets

from coverage import configs
from sampling.models.dataset import DatasetStats
from sampling.models.spread import Spread
from selector import strategies
from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row

# The track one of the sounder's traces covers, in kilometres.
TRACE_KM = configs.SHARAD_ALONG_TRACK_M / 1000.0

# How much further a corner to corner crossing runs than a straight one.
_DIAGONAL = math.sqrt(2.0)

_TILES = (
    "Strategy",
    "Tile width asked",
    "Tiles created",
    "Mean tile width",
    "Narrowest",
    "Widest",
)
_FILLING = (
    "Strategy",
    "Instrument",
    "Ground one pixel covers",
    "Pixels across a tile",
    "Pixels corner to corner",
    "Pixels to fill a tile",
)
_LANDED = (
    "Strategy",
    "Instrument",
    "Mean observations offered",
    "Mean pixels landed",
    "Mean pixels landed per observation",
    "Pixels asked",
)


def sizes(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how big a tile each strategy cuts its features into.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How big a tile is", _TILES, [_cut(stats) for stats in read.values()]
    )


def filling(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how much of each instrument it takes to cover a whole tile.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    rows, groups = _grouped(read, _fills)
    return tables.written("What it takes to fill a tile", _FILLING, rows, groups=groups)


def landed(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate what each instrument really lands on a tile and what is asked of it.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    rows, groups = _grouped(read, _lands)
    return tables.written(
        "What each instrument lands on a tile", _LANDED, rows, groups=groups
    )


def _grouped(
    read: Mapping[str, DatasetStats], write: Callable[[DatasetStats, str], Row]
) -> tuple[list[Row], list[int]]:
    """Write every strategy's instrument rows, each strategy ruled off the last.

    Args:
        read: What each strategy made of the features swept, by strategy name.
        write: How one instrument's row of one strategy is written.

    Returns:
        The rows, and the places a rule is drawn above.
    """
    rows: list[Row] = []
    groups: list[int] = []
    for stats in read.values():
        if rows:
            groups.append(len(rows))
        rows.extend(write(stats, iid) for iid in stats.iids)
    return rows, groups


def _cut(stats: DatasetStats) -> Row:
    """Write how big a tile one strategy cuts.

    Args:
        stats: What the strategy made of the features swept.

    Returns:
        The row.
    """
    wide = stats.widths
    return (
        stats.strategy,
        _km(strategies.named(stats.strategy).tile_km),
        f"{wide.counted:,}",
        wording.spread(wide, _km),
        _km(wide.low),
        _km(wide.high),
    )


def _fills(stats: DatasetStats, iid: str) -> Row:
    """Write how much of one instrument it takes to cover a whole tile.

    A sounder never fills an area, so its pixels are traces counted along the
    track it flies and it is credited with no count for filling a tile at all.

    Args:
        stats: What the strategy made of the features swept.
        iid: The instrument to write.

    Returns:
        The row.
    """
    tile_km = strategies.named(stats.strategy).tile_km
    sounder = iid == wording.SOUNDER
    pixel_km2 = stats.held.pixel_km2.get(iid)
    # The median, since a handful of records publish a pixel orders out from the rest
    ground = pixel_km2.middle if pixel_km2 and pixel_km2.counted else 0.0
    if not ground:
        return (stats.strategy, iid) + (wording.UNCOUNTED,) * 4
    across = TRACE_KM if sounder else math.sqrt(ground)
    return (
        stats.strategy,
        iid,
        f"{ground * 1e6:,.0f} m2",
        quantities.compact(tile_km / across),
        quantities.compact(tile_km * _DIAGONAL / across),
        wording.NOTHING if sounder else quantities.compact(tile_km * tile_km / ground),
    )


def _lands(stats: DatasetStats, iid: str) -> Row:
    """Write what one instrument offers a tile and what the strategy asks of it.

    Args:
        stats: What the strategy made of the features swept.
        iid: The instrument to write.

    Returns:
        Its observations, the pixels it lands, and the bar it clears.
    """
    asked = strategies.named(stats.strategy).admits.get(iid)
    landed_here = stats.held.landed.get(iid)
    per_look = stats.held.per_look.get(iid)
    return (
        stats.strategy,
        iid,
        wording.spread(stats.offered[iid], lambda counted: f"{counted:,.1f}"),
        wording.UNCOUNTED if landed_here is None else _pixels(landed_here, iid),
        wording.UNCOUNTED if not per_look else _written(per_look, iid),
        f"{asked:,.0f}" if asked else wording.NOTHING,
    )


def _pixels(measured: Spread, iid: str) -> str:
    """Write a pixel count read off many tiles, in the instrument's own units.

    Args:
        measured: The pixels it lands on a tile, tile by tile.
        iid: The instrument, which says whether its pixels are traces.

    Returns:
        The average, and how far the tiles sit from it where they disagree.
    """
    return wording.spread(measured, lambda counted: _written(counted, iid))


def _written(counted: float, iid: str) -> str:
    """Write one pixel count in the units the instrument measures in.

    Args:
        counted: The pixels.
        iid: The instrument, whose pixels are traces where it is the sounder.

    Returns:
        The count, unmarked for a sounder since its pixels are traces.
    """
    written = quantities.compact(counted)
    return written if iid == wording.SOUNDER else f"{written} px"


def _km(width_km: float) -> str:
    """Write a width in kilometres.

    Args:
        width_km: The width.

    Returns:
        The width, to a tenth below ten kilometres and whole above it.
    """
    return f"{width_km:,.0f} km" if width_km >= 10.0 else f"{width_km:,.1f} km"

"""How each strategy cuts the features up, and what lands on the tiles."""

from __future__ import annotations

import math
from collections.abc import Mapping

import ipywidgets as widgets

from analysis.coverage import configs
from analysis.sampling.models.dataset import DatasetStats
from analysis.sampling.models.spread import Spread
from analysis.selector import strategies
from analysis.utils.maths import quantities
from analysis.visualization.common import tables, wording
from analysis.visualization.common.tables import Row

# The track one of the sounder's traces covers, in kilometres.
_TRACE_KM = configs.SHARAD_ALONG_TRACK_M / 1000.0

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
    rows: list[Row] = []
    for stats in read.values():
        wide = stats.widths
        rows.append(
            (
                stats.strategy,
                _km(strategies.named(stats.strategy).tile_km),
                f"{wide.counted:,}",
                wording.spread(wide, _km),
                _km(wide.low),
                _km(wide.high),
            )
        )
    return tables.written("How big a tile is", _TILES, rows)


def filling(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how much of each instrument it takes to cover a whole tile.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    rows = [_fills(stats, iid) for stats in read.values() for iid in stats.iids]
    return tables.written("What it takes to fill a tile", _FILLING, rows)


def landed(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate what each instrument really lands on a tile and what is asked of it.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    rows = [_lands(stats, iid) for stats in read.values() for iid in stats.iids]
    return tables.written("What each instrument lands on a tile", _LANDED, rows)


def _fills(stats: DatasetStats, iid: str) -> Row:
    """Write how much of one instrument it takes to cover a whole tile.

    A sounder never fills an area, so its pixels are traces counted along the
    track it flies and it is credited with no count for filling a tile at all.

    Args:
        stats: What the strategy made of the features swept.
        iid: The instrument to write.

    Returns:
        The row, reading nothing at all where no pixel size is known.
    """
    measured = stats.tiles.pixel_km2.get(iid)
    # The median, since a handful of records publish a pixel orders out from the rest
    ground = measured.middle if measured and measured.counted else 0.0
    if not ground:
        return (stats.strategy, iid) + (wording.UNCOUNTED,) * 4
    sounder = iid == wording.SOUNDER
    tile_km = strategies.named(stats.strategy).tile_km
    across = _TRACE_KM if sounder else math.sqrt(ground)
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

    def counted(measured: Spread | None) -> str:
        """Write a pixel count read off many tiles, in the instrument's own units."""
        if measured is None or not measured.counted:
            return wording.UNCOUNTED
        return wording.spread(measured, lambda pixels: _written(pixels, iid))

    return (
        stats.strategy,
        iid,
        wording.spread(stats.offered[iid], lambda offered: f"{offered:,.1f}"),
        counted(stats.tiles.landed.get(iid)),
        counted(stats.tiles.pixels_per_look.get(iid)),
        f"{asked:,.0f}" if asked else wording.NOTHING,
    )


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

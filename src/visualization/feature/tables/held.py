"""The tile on show, and everything the search left on it."""

from __future__ import annotations

import ipywidgets as widgets

from sampling import measuring
from sampling.models.tiles import TileStats
from utils.maths import quantities
from visualization.common import panels, tables, wording
from visualization.common.tables import Row
from visualization.feature import picker
from visualization.feature.picker import TileView

_HEADINGS = ("On this tile", "What it holds")
_NONE = "-"


def plot(chosen: TileView | None) -> widgets.Widget:
    """Summarise what the search left on the tile on show.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The table as a widget, or the grey panel when no tile is picked.
    """
    if chosen is None:
        return panels.unavailable(picker.NO_TILE)
    return tables.written(
        f"{chosen.name}  -  what it holds", _HEADINGS, _rows(chosen.stats)
    )


def _rows(stats: TileStats) -> list[Row]:
    """Write out everything the tile holds.

    Args:
        stats: The tile, as the search left it.

    Returns:
        Every row, the tile itself first and what each instrument left last.
    """
    written: list[Row] = [
        ("Ground the tile covers", quantities.area(stats.area_km2)),
        ("How long its window lasts", _window(stats)),
        ("Ground its window reaches", f"{stats.geo_mean:.0%}" if stats.kept else _NONE),
        (
            "Looks too small inside the window",
            f"{stats.refused:,}, with {stats.turned_away:,} too small for the tile "
            f"at all",
        ),
        (
            "Pixels its window holds",
            wording.pixels(_pixels(stats)) if stats.kept else _NONE,
        ),
    ]
    written += [
        (f"Ground {iid} reaches", _reach(stats, iid)) for iid in sorted(stats.reached)
    ]
    written += [
        (
            f"Ground reached by {wording.counted(shared, 'instrument')}",
            wording.ground(km2, stats.area_km2),
        )
        for shared, km2 in measuring.ground_by_instrument_count(stats.overlaps).items()
    ]
    return written


def _window(stats: TileStats) -> str:
    """Say how long the tile's window lasts and when it is open.

    Args:
        stats: The tile, as the search left it.

    Returns:
        The length and the dates, or that the tile earned no window.
    """
    if not stats.kept or stats.start is None or stats.end is None:
        return _NONE
    return (
        f"{quantities.duration(stats.days)}, "
        f"{stats.start:%Y-%m-%d} to {stats.end:%Y-%m-%d}"
    )


def _reach(stats: TileStats, iid: str) -> str:
    """Write what one instrument left on the tile.

    Args:
        stats: The tile, as the search left it.
        iid: The instrument the row is written for.

    Returns:
        The share of the tile it reaches, its pixels, and how many it keeps.
    """
    reach = stats.reached[iid]
    share = f"{reach.km2 / stats.area_km2:.0%}" if stats.area_km2 else wording.NOTHING
    taken = wording.counted(reach.observations_taken, "observation")
    return f"{share}, {wording.pixels(reach.pixels)}, from {taken}"


def _pixels(stats: TileStats) -> float | None:
    """Add up the pixels the tile keeps.

    Args:
        stats: The tile, as the search left it.

    Returns:
        The total, or None when any instrument carries no count.
    """
    counted = [reach.pixels for reach in stats.reached.values()]
    if any(count is None for count in counted):
        return None
    return sum(count for count in counted if count is not None)

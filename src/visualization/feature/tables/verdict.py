"""Which tiles of the feature the search kept, one row each."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import ipywidgets as widgets

from utils.maths import quantities
from visualization.common import panels, surveys, tables, tiles, wording
from visualization.common.picker import View
from visualization.common.tables import Mark, Row
from visualization.common.tiles import TileStats

# How a tile that belongs in the dataset is marked, and one that does not.
VERDICT_PASS = "#2e7d32"
VERDICT_FAIL = "#c62828"
VERDICT_KEPT = "In the dataset"
VERDICT_LEFT = "Left out of the dataset"

_HEADINGS = ("Tile", "Ground", "Observations", "Window", "Reached", "Pixels", "")
_NOTHING = "No instrument set filled a cell of this feature."
_NONE = "-"


def plot(view: View) -> widgets.Widget:
    """Report which tiles of the feature earned a window, and which did not.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The table as a widget, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    study = surveys.studied(view.coverage, view.strategy)
    if not study.gridded:
        return panels.unavailable(_NOTHING)
    measured = tiles.measured(study)
    kept = any(tile.kept for tile in measured)
    table = tables.written(
        f"{panels.title(view.coverage)}  -  tile by tile",
        _HEADINGS,
        [_row(tile) for tile in measured],
        lead=f"searched under {view.strategy.name}",
    )
    return widgets.VBox([_headline(kept), table])


def _headline(kept: bool) -> widgets.HTML:
    """Write whether the feature belongs in the dataset at all.

    Args:
        kept: Whether any tile earned a window.

    Returns:
        The banner, coloured by which way it went.
    """
    colour = VERDICT_PASS if kept else VERDICT_FAIL
    said = VERDICT_KEPT if kept else VERDICT_LEFT
    return widgets.HTML(
        f'<div style="font-family: sans-serif; color: {colour}; font-size: 15px;'
        f' font-weight: 600; margin: 6px 0 0 0;">{escape(said)}</div>'
    )


def _row(tile: TileStats) -> Row:
    """Write one tile's row.

    Args:
        tile: The tile, as the search left it.

    Returns:
        The row, marked by whether the tile earned a window.
    """
    mark = Mark(*(("PASS", VERDICT_PASS) if tile.kept else ("NOT PASS", VERDICT_FAIL)))
    return (
        wording.tile(tile.row, tile.column),
        quantities.area(tile.area_km2),
        f"{tile.taken:,} of {tile.taken + tile.dropped:,}",
        quantities.duration(tile.days) if tile.kept else _NONE,
        f"{tile.reach:.0%}" if tile.kept else _NONE,
        wording.pixels(_pixels(tile)) if tile.kept else _NONE,
        mark,
    )


def _pixels(tile: TileStats) -> float | None:
    """Add up the pixels the tile's window holds.

    Args:
        tile: The tile, as the search left it.

    Returns:
        The total, or None when any instrument carries no count.
    """
    counted: Sequence[float | None] = [reach.pixels for reach in tile.reached.values()]
    if any(count is None for count in counted):
        return None
    return sum(count for count in counted if count is not None)

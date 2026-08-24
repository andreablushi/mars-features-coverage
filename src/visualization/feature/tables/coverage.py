"""What each instrument reached on the tile on show, in ground and in pixels."""

from __future__ import annotations

import ipywidgets as widgets

from utils.maths import quantities
from visualization.common import panels, tables, wording
from visualization.common.picker import View
from visualization.common.tables import Row
from visualization.common.tiles import TileStats
from visualization.feature import picker
from visualization.feature.picker import TileView

_HEADINGS = (
    "Instrument",
    "Observations kept",
    "Ground reached",
    "Share of the tile",
    "Pixels",
)
_NO_WINDOW = "This tile holds no window worth keeping."


def plot(chosen: TileView | None) -> widgets.Widget:
    """Tabulate what each instrument reached on the tile on show.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The table as a widget, or the grey panel when no window was earned.
    """
    if chosen is None:
        return panels.unavailable(picker.NO_TILE)
    if chosen.survey is None:
        return panels.unavailable(_NO_WINDOW)
    stats = chosen.stats
    return tables.written(
        f"{chosen.name}  -  inside its window",
        _HEADINGS,
        [_row(stats, iid) for iid in sorted(stats.reached)],
        lead=_when(chosen.view, stats),
    )


def _when(view: View, stats: TileStats) -> str:
    """Say when the tile's window is open and how long it runs.

    Args:
        view: The feature on show and the strategy it is judged under.
        stats: The tile, as the search left it.

    Returns:
        The line under the title.
    """
    return (
        f"{view.strategy.name}, {stats.start:%Y-%m-%d} to {stats.end:%Y-%m-%d}, "
        f"{quantities.duration(stats.days)} over "
        f"{quantities.area(stats.area_km2)} of feature"
    )


def _row(stats: TileStats, iid: str) -> Row:
    """Write one instrument's row.

    Args:
        stats: The tile, as the search left it.
        iid: The instrument the row describes.

    Returns:
        The row.
    """
    reach = stats.reached[iid]
    return (
        iid,
        f"{reach.taken:,}",
        quantities.area(reach.km2),
        f"{reach.km2 / stats.area_km2:.0%}" if stats.area_km2 else wording.NOTHING,
        wording.pixels(reach.pixels),
    )

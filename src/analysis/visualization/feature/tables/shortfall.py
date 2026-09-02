"""Why the tile on show earned no window, and what it came closest with."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.visualization.common import panels, tables
from analysis.visualization.common.tables import Row
from analysis.visualization.feature import picker
from analysis.visualization.feature.picker import TileView
from analysis.visualization.feature.stats import shortfall
from analysis.visualization.feature.stats.shortfall import Shortfall

_HEADINGS = (
    "Asked of",
    "Share asked",
    "In the best window",
    "Over the whole record",
)
_WHOLE_RECORD = "whole record"


def plot(chosen: TileView | None) -> widgets.Widget:
    """Report what the tile on show could hold when no ground is asked of it.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The table as a widget, or the grey panel when no tile is picked.
    """
    if chosen is None:
        return panels.unavailable(picker.NO_TILE)
    return tables.written(
        f"{chosen.name}  -  the most it could bring",
        _HEADINGS,
        [_row(asked) for asked in shortfall.best(chosen)],
    )


def _row(asked: Shortfall) -> Row:
    """Write what one instrument is asked of the tile and the most it brings.

    Args:
        asked: What it is asked, and what it reaches in the window and in all.

    Returns:
        The row, the share asked beside the shares reached so a shortfall reads off it.
    """
    named = f"{asked.iid} ({_WHOLE_RECORD})" if asked.timeless else asked.iid
    return (
        named,
        f"{asked.asked:.0%}",
        f"{asked.windowed:.0%}",
        f"{asked.whole:.0%}",
    )

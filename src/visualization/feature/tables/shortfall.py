"""Why the tile on show earned no window, and what it came closest with."""

from __future__ import annotations

import ipywidgets as widgets

from visualization.common import panels, tables
from visualization.common.tables import Mark, Row
from visualization.feature import picker
from visualization.feature.picker import TileView
from visualization.feature.stats import shortfall
from visualization.feature.stats.shortfall import Shortfall

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
    attempt = shortfall.best(chosen)
    return tables.written(
        f"{chosen.name}  -  the most it could bring",
        _HEADINGS,
        [_row(asked) for asked in attempt.asked],
    )


def _row(asked: Shortfall) -> Row:
    """Write what one instrument is asked of the tile and the most it brings.

    Args:
        asked: What it is asked, and what it reaches in the window and in all.

    Returns:
        The row, with a share short of what was asked marked out.
    """
    named = f"{asked.iid} ({_WHOLE_RECORD})" if asked.timeless else asked.iid
    return (
        named,
        f"{asked.asked:.0%}",
        _marked(asked.windowed, asked.met),
        _marked(asked.whole, asked.reachable),
    )


def _marked(reached: float, met: bool) -> Mark:
    """Write one share, coloured by whether it brings what was asked.

    Args:
        reached: The share of the tile reached.
        met: Whether that is enough.

    Returns:
        The cell.
    """
    return Mark(f"{reached:.0%}", panels.KEPT if met else panels.REFUSED)

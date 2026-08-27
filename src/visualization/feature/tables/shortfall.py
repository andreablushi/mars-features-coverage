"""Why the tile on show earned no window, and what it came closest with."""

from __future__ import annotations

import ipywidgets as widgets

from sampling.models.tiles import TileStats
from utils.maths import quantities
from visualization.common import panels, tables
from visualization.common.tables import Mark, Row
from visualization.feature import picker
from visualization.feature.picker import TileView
from visualization.feature.stats import shortfall
from visualization.feature.stats.shortfall import Attempt, Shortfall

_HEADINGS = (
    "Asked of",
    "Share asked",
    "In the best window",
    "Over the whole record",
)
_NONE = "-"
_WHOLE_RECORD = "whole record"
_NO_WINDOW = (
    "No window at all, even with no ground asked: an instrument the strategy "
    "names left nothing on this tile."
)
_NOTE = (
    "The best window is the one scoring highest once the ground bars are lifted, "
    "so an instrument short of its bar there may still reach it in some other "
    "window. The whole record is the most it ever reaches, so an instrument short "
    "there can never answer for this tile at all."
)


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
        lead=_lead(chosen, attempt),
        note=_NOTE,
    )


def _lead(chosen: TileView, attempt: Attempt) -> str:
    """Say what the tile made of the search, and what the unfloored one found.

    Args:
        chosen: The tile on show.
        attempt: What it brings when no ground is asked of it.

    Returns:
        The grey line set under the title.
    """
    verdict = (
        "earned a window"
        if chosen.stats.kept
        else "earned no window, so what follows is what it fell short of"
    )
    under = f"searched under {chosen.view.strategy.name}, {verdict}"
    if attempt.stats is None:
        return f"{under}. {_NO_WINDOW}"
    return f"{under}. With no ground asked, the best window {_window(attempt.stats)}"


def _window(stats: TileStats) -> str:
    """Say how long the unfloored window runs and when it is open.

    Args:
        stats: The tile as the unfloored search left it.

    Returns:
        The length and the dates it runs between.
    """
    if stats.start is None or stats.end is None:
        return _NONE
    return (
        f"runs {quantities.duration(stats.days)}, "
        f"{stats.start:%Y-%m-%d} to {stats.end:%Y-%m-%d}"
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

"""Why the feature on show earned no window, and what it came closest with."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.visualization.common import panels, tables
from analysis.visualization.common.picker import View
from analysis.visualization.common.tables import Row
from analysis.visualization.feature.stats import shortfall
from analysis.visualization.feature.stats.shortfall import Shortfall

_HEADINGS = (
    "Asked of",
    "Share asked",
    "In the best window",
    "Over the whole record",
)
_WHOLE_RECORD = "whole record"


def plot(view: View) -> widgets.Widget:
    """Report what the feature on show could hold when no ground is asked of it.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The table as a widget, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    return tables.written(
        f"{panels.title(view.coverage)}  -  the most it could bring",
        _HEADINGS,
        [_row(asked) for asked in shortfall.best(view)],
    )


def _row(asked: Shortfall) -> Row:
    """Write what one instrument is asked of the feature and the most it brings.

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

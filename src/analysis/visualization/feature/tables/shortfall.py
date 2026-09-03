"""Why the feature on show earned no window, and what it came closest with."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.visualization.common import panels, tables
from analysis.visualization.common.picker import Coverage
from analysis.visualization.feature.stats import shortfall

_HEADINGS = (
    "Asked of",
    "Share asked",
    "In the best window",
    "Over the whole record",
)
_WHOLE_RECORD = "whole record"


def plot(coverage: Coverage) -> widgets.Widget:
    """Report what the feature on show could hold when no ground is asked of it.

    Args:
        coverage: The feature on show, as the instrument sets it holds.

    Returns:
        The table as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    # The share asked sits beside the shares reached, so a shortfall reads off the row
    return tables.written(
        f"{panels.title(coverage)}  -  the most it could bring",
        _HEADINGS,
        [
            (
                f"{asked.iid} ({_WHOLE_RECORD})" if asked.timeless else asked.iid,
                f"{asked.asked:.0%}",
                f"{asked.windowed:.0%}",
                f"{asked.whole:.0%}",
            )
            for asked in shortfall.best(coverage)
        ],
    )

"""How much ground the windows reach, and how long they run to reach it."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.sampling.models.dataset import DatasetStats
from analysis.sampling.models.spread import Spread
from analysis.utils.maths import quantities
from analysis.visualization.common import tables, wording
from analysis.visualization.common.tables import Row

_REACHED = ("Reached by", "Mean coverage inside a feature", "Least")
_WINDOWS = ("Statistic", "Value")

# What the row holding the ground every instrument reaches at once is called.
_OVERLAP = "Every instrument at once"


def reached(read: DatasetStats) -> widgets.Widget:
    """Tabulate how much of a feature each instrument reaches and how much they share.

    Args:
        read: What the filter made of the features swept.

    Returns:
        The table as a widget.
    """
    rows = [_share(iid, read.held.reached[iid]) for iid in read.iids]
    rows.append(_share(_OVERLAP, read.overlap))
    return tables.written(
        "How much of a feature each instrument reaches", _REACHED, rows
    )


def windows(read: DatasetStats) -> widgets.Widget:
    """Tabulate how long the windows run and how far they reach.

    Args:
        read: What the filter made of the features swept.

    Returns:
        The table as a widget, read down rather than across since one filter
        leaves one window to report.
    """
    days = read.held.days
    return tables.written(
        "How long a window runs",
        _WINDOWS,
        [
            ("Mean window", wording.spread(days, quantities.duration)),
            (
                "Longest window",
                quantities.duration(days.high) if days.counted else wording.NOTHING,
            ),
            ("Time Window Score", wording.spread(read.held.geo_mean, _percent)),
        ],
    )


def _share(name: str, measured: Spread) -> Row:
    """Write one share read off every feature that earned a window.

    Args:
        name: What the share is of, such as an instrument or a count of them.
        measured: The share, feature by feature.

    Returns:
        The row.
    """
    return (
        name,
        wording.spread(measured, _percent),
        _percent(measured.low) if measured.counted else wording.NOTHING,
    )


def _percent(share: float) -> str:
    """Write a share as a percentage.

    Args:
        share: The share, from nought to one.

    Returns:
        The percentage, to one decimal place.
    """
    return f"{share:.1%}"

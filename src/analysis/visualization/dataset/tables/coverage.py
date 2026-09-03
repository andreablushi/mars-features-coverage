"""How much ground the windows reach, and how long they run to reach it."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.stats.models.dataset import DatasetStats
from analysis.stats.models.spread import Spread
from analysis.utils.maths import quantities
from analysis.visualization.common import tables, wording
from analysis.visualization.common.models.tables import Row

_REACHED = ("Reached by", "Mean coverage inside a feature", "Least")
_WINDOWS = ("Statistic", "Value")
_OVERLAP = "Every instrument at once"


def reached(read: DatasetStats) -> widgets.Widget:
    """Tabulate how much of a feature each instrument reaches, and what they share."""
    rows = [_share(iid, read.held.reached[iid]) for iid in read.iids]
    rows.append(_share(_OVERLAP, read.overlap))
    return tables.written(
        "How much of a feature each instrument reaches", _REACHED, rows
    )


def windows(read: DatasetStats) -> widgets.Widget:
    """Tabulate how long the windows run and how far they reach."""
    days = read.held.days
    return tables.written(
        "How long a window runs",
        _WINDOWS,
        [
            ("Mean window", wording.spread(days, quantities.duration)),
            ("Longest window", quantities.duration(days.high)),
            (
                "Time Window Score",
                wording.spread(read.held.geo_mean, lambda share: f"{share:.1%}"),
            ),
        ],
    )


def _share(name: str, measured: Spread) -> Row:
    """Write one share read off every feature that earned a window."""
    return (
        name,
        wording.spread(measured, lambda share: f"{share:.1%}"),
        f"{measured.low:.1%}",
    )

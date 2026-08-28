"""How much ground the windows reach, and how long they run to reach it."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from sampling.models.dataset import DatasetStats
from sampling.models.spread import Spread
from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row

_REACHED = ("Strategy", "Instrument", "Mean coverage inside a tile", "Least")
_WINDOWS = ("Strategy", "Mean window", "Longest", "Time Window Score")

# What the row holding the ground every instrument reaches at once is called.
OVERLAP = "Overlap"


def reached(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how much of a tile each instrument reaches and how much they share.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    rows: list[Row] = []
    # Every strategy after the first is ruled off from the one above it
    groups: list[int] = []
    for stats in read.values():
        if rows:
            groups.append(len(rows))
        rows.extend(
            _share(stats.strategy, iid, stats.held.reached[iid]) for iid in stats.iids
        )
        rows.append(_share(stats.strategy, OVERLAP, stats.overlap))
    return tables.written(
        "How much of a tile each instrument reaches", _REACHED, rows, groups=groups
    )


def windows(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how long each strategy's windows run and how far they reach.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How long a window runs", _WINDOWS, [_length(stats) for stats in read.values()]
    )


def _share(strategy: str, name: str, measured: Spread) -> Row:
    """Write one share read off every tile that earned a window.

    Args:
        strategy: The strategy the tiles were searched under.
        name: What the share is of, such as an instrument or a count of them.
        measured: The share, tile by tile.

    Returns:
        The row.
    """
    return (
        strategy,
        name,
        wording.spread(measured, _percent),
        _percent(measured.low) if measured.counted else wording.NOTHING,
    )


def _length(stats: DatasetStats) -> Row:
    """Write how long one strategy's windows run.

    Args:
        stats: What it made of the features swept.

    Returns:
        The row.
    """
    days, score = stats.held.days, stats.held.geo_mean
    return (
        stats.strategy,
        wording.spread(days, quantities.duration),
        quantities.duration(days.high) if days.counted else wording.NOTHING,
        wording.spread(score, _percent),
    )


def _percent(share: float) -> str:
    """Write a share as a percentage.

    Args:
        share: The share, from nought to one.

    Returns:
        The percentage, to one decimal place.
    """
    return f"{share:.1%}"

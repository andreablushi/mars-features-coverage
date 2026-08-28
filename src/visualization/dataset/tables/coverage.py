"""How much ground the windows reach, and how long they run to reach it."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from sampling.models.dataset import DatasetStats
from sampling.models.spread import Spread
from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row

_REACHED = (
    "Strategy",
    "Instrument",
    "Mean of a tile",
    "Spread",
    "Least",
)

# What the row holding the ground every instrument reaches at once is called.
OVERLAP = "Overlap"
_WINDOWS = (
    "Strategy",
    "Mean window",
    "Spread",
    "Longest",
    "Coverage score",
    "Spread",
)


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
        rows.extend(_reaching(stats))
    return tables.written(
        "How much of a tile each instrument reaches",
        _REACHED,
        rows,
        groups=groups,
    )


def _reaching(stats: DatasetStats) -> list[Row]:
    """Write one strategy's rows, an instrument each and the overlap last.

    Args:
        stats: What it made of the features swept.

    Returns:
        The rows, in the order the instruments are drawn.
    """
    rows = [_share(stats.strategy, iid, stats.held.reached[iid]) for iid in stats.iids]
    return rows + [_share(stats.strategy, OVERLAP, stats.overlap)]


def windows(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how long each strategy's windows run and how far they reach.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How long a window runs",
        _WINDOWS,
        [_length(stats) for stats in read.values()],
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
        f"{measured.mean:.1%}",
        f"± {measured.deviation:.1%}",
        f"{measured.low:.1%}",
    )


def _length(stats: DatasetStats) -> Row:
    """Write how long one strategy's windows run.

    Args:
        stats: What it made of the features swept.

    Returns:
        The row.
    """
    days, geo_mean = stats.held.days, stats.held.geo_mean
    if not days.counted:
        return (stats.strategy,) + (wording.NOTHING,) * 5
    return (
        stats.strategy,
        quantities.duration(days.mean),
        f"± {quantities.duration(days.deviation)}",
        quantities.duration(days.high),
        f"{geo_mean.mean:.1%}",
        f"± {geo_mean.deviation:.1%}",
    )

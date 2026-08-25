"""How much ground the windows reach, and how long they run to reach it."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.spread import Spread
from visualization.common.tables import Row
from visualization.dataset.stats.dataset import DatasetStats

_REACHED = ("Strategy", "Instrument", "Mean of a tile", "Spread", "Least", "Most")
_SHARED = ("Strategy", "Instruments", "Mean of a tile", "Spread", "Least", "Most")
_WINDOWS = (
    "Strategy",
    "Mean window",
    "Spread",
    "Shortest",
    "Longest",
    "Ground a window reaches",
    "Spread",
)
_REACHED_NOTE = (
    "Every tile that earned a window counts, including those one instrument "
    "never reached."
)
_SHARED_NOTE = (
    "A cell counts once, under the instruments really on it, so the rows do "
    "not overlap and add up to the ground a window reaches."
)


def reached(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how much of a tile each instrument reaches, strategy by strategy.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How much of a tile each instrument reaches",
        _REACHED,
        [
            _share(stats.strategy, iid, stats.held.reached[iid])
            for stats in read.values()
            for iid in stats.iids
        ],
        note=_REACHED_NOTE,
    )


def shared(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how much of a tile the instruments overlap on.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "Where the instruments overlap",
        _SHARED,
        [
            _share(stats.strategy, _named(counted), measured)
            for stats in read.values()
            for counted, measured in stats.shared.items()
        ],
        note=_SHARED_NOTE,
    )


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
        lead="measured over the tiles that earned a window",
    )


def _named(counted: int) -> str:
    """Say how many instruments reach a piece of ground.

    Args:
        counted: How many of them there are.

    Returns:
        The phrase the row is written under.
    """
    return "1 instrument" if counted == 1 else f"{counted} instruments"


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
        f"{measured.high:.1%}",
    )


def _length(stats: DatasetStats) -> Row:
    """Write how long one strategy's windows run.

    Args:
        stats: What it made of the features swept.

    Returns:
        The row.
    """
    days, reach = stats.held.days, stats.held.reach
    if not days.counted:
        return (stats.strategy,) + (wording.NOTHING,) * 6
    return (
        stats.strategy,
        quantities.duration(days.mean),
        f"± {quantities.duration(days.deviation)}",
        quantities.duration(days.low),
        quantities.duration(days.high),
        f"{reach.mean:.1%}",
        f"± {reach.deviation:.1%}",
    )

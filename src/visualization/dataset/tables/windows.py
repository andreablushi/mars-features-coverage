"""How long the windows run, and what they keep of what they were offered."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row
from visualization.dataset.stats.dataset import DatasetStats

_WINDOWS = (
    "Strategy",
    "Middle window",
    "Mean window",
    "Spread",
    "Ground a window reaches",
    "Spread",
)
_TAKEN = (
    "Strategy",
    "Observations kept",
    "Dropped as repeats",
    "Too small inside a window",
    "Too small for a tile",
    "Pixels kept",
)
_CLASSES = ("Feature class",)


def lengths(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how long each strategy's windows run.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How long the windows run",
        _WINDOWS,
        [_length(stats) for stats in read.values()],
        lead="measured over the tiles that earned a window",
    )


def taken(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate what each strategy keeps of the observations it was offered.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "What the windows keep",
        _TAKEN,
        [_kept(stats) for stats in read.values()],
        lead="counted once per tile an observation was offered to",
    )


def classes(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how many features of each class each strategy keeps.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    names = list(read)
    every = {
        feature_class: counted
        for stats in read.values()
        for feature_class, (_, counted) in stats.classes.items()
    }
    return tables.written(
        "Which feature classes survive",
        _CLASSES + tuple(names),
        [
            _row(feature_class, counted, read)
            for feature_class, counted in every.items()
        ],
        lead="features kept of the features searched, class by class",
    )


def _length(stats: DatasetStats) -> Row:
    """Write one strategy's window lengths.

    Args:
        stats: What it made of the features swept.

    Returns:
        The row.
    """
    days, reach = stats.held.days, stats.held.reach
    return (
        stats.strategy,
        quantities.duration(days.middle) if days.counted else wording.NOTHING,
        quantities.duration(days.mean) if days.counted else wording.NOTHING,
        f"± {quantities.duration(days.deviation)}" if days.counted else wording.NOTHING,
        f"{reach.mean:.1%}" if reach.counted else wording.NOTHING,
        f"± {reach.deviation:.1%}" if reach.counted else wording.NOTHING,
    )


def _kept(stats: DatasetStats) -> Row:
    """Write what one strategy keeps of what it was offered.

    Args:
        stats: What it made of the features swept.

    Returns:
        The row.
    """
    held = stats.held
    counted = [count for count in held.pixels.values() if count is not None]
    whole = None if len(counted) < len(held.pixels) else sum(counted)
    return (
        stats.strategy,
        f"{held.taken:,}",
        f"{held.dropped:,}",
        f"{held.refused:,}",
        f"{held.turned_away:,}",
        wording.pixels(whole),
    )


def _row(feature_class: str, counted: int, read: Mapping[str, DatasetStats]) -> Row:
    """Write one feature class's row.

    Args:
        feature_class: The class, such as Crater.
        counted: How many features of it were searched.
        read: What each strategy made of the features swept.

    Returns:
        The row, one cell per strategy.
    """
    return (f"{feature_class} ({counted:,})",) + tuple(
        f"{stats.classes.get(feature_class, (0, 0))[0]:,}" for stats in read.values()
    )

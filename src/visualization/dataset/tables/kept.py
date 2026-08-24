"""What each strategy would leave in the dataset, side by side."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from survey import strategies
from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row
from visualization.dataset.stats.dataset import DatasetStats

_HEADINGS = (
    "Strategy",
    "Features kept",
    "Tiles searched",
    "Tiles kept",
    "Tiles removed",
    "Tiles per feature",
    "Ground kept",
)
_ASKED = (
    "Strategy",
    "Instruments insisted on",
    "Together",
    "Longest window",
    "Timeless",
)


def plot(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate what every strategy would leave in the dataset.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "What each strategy keeps",
        _HEADINGS,
        [_row(stats) for stats in read.values()],
        lead=_lead(read),
    )


def asked(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate what every strategy asks of a window.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "What each strategy asks",
        _ASKED,
        [_demanded(name) for name in read],
    )


def _lead(read: Mapping[str, DatasetStats]) -> str:
    """Say how much of the catalogue the sweep covered.

    Args:
        read: What each strategy made of the features swept.

    Returns:
        The line under the title.
    """
    if not read:
        return "nothing swept yet"
    first = next(iter(read.values()))
    return f"{first.features:,} features swept, {first.gridded:,} holding ground"


def _row(stats: DatasetStats) -> Row:
    """Write one strategy's row.

    Args:
        stats: What it made of the features swept.

    Returns:
        The row.
    """
    held = stats.held
    return (
        stats.strategy,
        f"{stats.kept:,} of {stats.features:,}",
        f"{held.searched:,}",
        f"{held.kept:,}",
        f"{held.searched - held.kept:,}",
        f"{stats.split.middle:,.0f} in the middle, {stats.split.mean:,.1f} on average",
        wording.ground(held.kept_km2, held.area_km2),
    )


def _demanded(name: str) -> Row:
    """Write what one strategy asks of a window.

    Args:
        name: The strategy's name.

    Returns:
        The row.
    """
    strategy = strategies.named(name)
    return (
        name,
        ", ".join(
            " or ".join(f"{iid} {share:.0%}" for iid, share in demand.items())
            for demand in strategy.demands
        ),
        f"{strategy.together:.0%}",
        quantities.duration(strategy.span_days),
        ", ".join(sorted(strategy.timeless)) or wording.NOTHING,
    )

"""How much of a tile each instrument reaches, and where they overlap."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row
from visualization.dataset.stats.dataset import DatasetStats

_COVERAGE = (
    "Strategy",
    "Instrument",
    "Mean of a tile",
    "Middle tile",
    "Spread",
    "Least",
    "Most",
    "Pixels",
)
_OVERLAP = ("Strategy", "Instruments", "Ground", "Share of the ground kept")
_NOTE = (
    "Every tile that earned a window counts, including those one instrument "
    "never reached."
)


def coverage(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how much of a tile each instrument reaches, strategy by strategy.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How much of a tile each instrument reaches",
        _COVERAGE,
        [_reach(stats, iid) for stats in read.values() for iid in stats.iids],
        note=_NOTE,
    )


def overlap(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how much ground the instruments reach between them.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "Where the instruments overlap",
        _OVERLAP,
        [
            _shared(stats, names, km2)
            for stats in read.values()
            for names, km2 in stats.held.overlaps.items()
        ],
        lead="a cell counts once, under the instruments really there",
    )


def _reach(stats: DatasetStats, iid: str) -> Row:
    """Write one instrument's row under one strategy.

    Args:
        stats: What the strategy made of the features swept.
        iid: The instrument the row describes.

    Returns:
        The row.
    """
    measured = stats.held.reached[iid]
    return (
        stats.strategy,
        iid,
        f"{measured.mean:.1%}",
        f"{measured.middle:.1%}",
        f"± {measured.deviation:.1%}",
        f"{measured.low:.1%}",
        f"{measured.high:.1%}",
        wording.pixels(stats.held.pixels[iid]),
    )


def _shared(stats: DatasetStats, names: tuple[str, ...], km2: float) -> Row:
    """Write one set of instruments' row under one strategy.

    Args:
        stats: What the strategy made of the features swept.
        names: The instruments reaching the ground.
        km2: How much of it they reach.

    Returns:
        The row.
    """
    return (
        stats.strategy,
        " and ".join(names),
        quantities.area(km2),
        f"{km2 / stats.held.kept_km2:.0%}" if stats.held.kept_km2 else wording.NOTHING,
    )

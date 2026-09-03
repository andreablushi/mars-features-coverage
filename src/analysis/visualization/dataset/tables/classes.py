"""What the filter leaves of the features of each class."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.stats.models.catalogue import CatalogueStats
from analysis.stats.models.dataset import DatasetStats
from analysis.visualization.common import tables, wording
from analysis.visualization.common.models.tables import Row

_SELECTED = (
    "Feature class",
    "Features measured",
    "Features selected",
    "Share selected",
)


def selected(stats: CatalogueStats, read: DatasetStats) -> widgets.Widget:
    """Tabulate how many features of each class the filter selects."""
    rows: list[Row] = []
    for name, measured in stats.classes.items():
        made = read.classes.get(name)
        taken = made.selected if made else 0
        rows.append(
            (
                name,
                f"{measured:,}",
                f"{taken:,}" if taken else wording.NOTHING,
                f"{taken / measured:.0%}" if taken else wording.NOTHING,
            )
        )
    return tables.written(
        "How many features of each class the filter selects", _SELECTED, rows
    )


def taken(stats: CatalogueStats, read: DatasetStats) -> widgets.Widget:
    """Tabulate how many observations of a feature of each class are kept."""
    rows: list[Row] = []
    for name in stats.classes:
        made = read.classes.get(name)
        cells = [
            wording.spread(made.taken[iid], lambda counted: f"{counted:,.0f}")
            if made
            else wording.NOTHING
            for iid in read.iids
        ]
        rows.append((name, *cells))
    return tables.written(
        "How many observations of a selected feature each instrument keeps",
        ("Feature class",) + tuple(read.iids),
        rows,
    )

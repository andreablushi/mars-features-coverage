"""What each feature class holds, and what the filter leaves of it."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.stats.models.catalogue import CatalogueStats
from analysis.stats.models.dataset import DatasetStats
from analysis.visualization.common import quantities, tables, wording
from analysis.visualization.common.models.tables import Row

_HEADINGS = (
    "Feature class",
    "Features measured",
    "Mean feature size",
    "Features selected",
)


def held(stats: CatalogueStats, read: DatasetStats) -> widgets.Widget:
    """Tabulate what each class holds and what the filter keeps of it."""
    rows: list[Row] = []
    for name, measured in stats.classes.items():
        made = read.classes.get(name)
        rows.append(
            (
                name,
                f"{measured:,}",
                wording.spread(stats.class_km2[name], quantities.area),
                f"{made.selected:,}" if made else wording.NOTHING,
                *(
                    wording.spread(made.taken[iid], lambda counted: f"{counted:,.0f}")
                    if made
                    else wording.NOTHING
                    for iid in read.iids
                ),
            )
        )
    return tables.written(
        "What each feature class holds and what the filter keeps of it",
        _HEADINGS + tuple(read.iids),
        rows,
    )

"""What the filter would make of the features of each class."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.sampling.models.catalogue import CatalogueStats
from analysis.sampling.models.dataset import ClassStats, DatasetStats
from analysis.visualization.common import tables, wording
from analysis.visualization.common.tables import Row

_SELECTED = (
    "Feature class",
    "Features measured",
    "Features selected",
    "Share selected",
)


def selected(stats: CatalogueStats, read: DatasetStats) -> widgets.Widget:
    """Tabulate how many features of each class the filter would select.

    Args:
        stats: What the catalogue index holds, which orders the classes.
        read: What the filter made of the features swept.

    Returns:
        The table as a widget, reading nothing where it selected none of a class.
    """
    rows: list[Row] = []
    for name, measured in stats.classes.items():
        made = read.classes.get(name)
        taken = made.selected if made else 0
        rows.append(
            (
                name,
                f"{measured:,}",
                f"{taken:,}" if taken else wording.NOTHING,
                f"{taken / measured:.0%}" if taken and measured else wording.NOTHING,
            )
        )
    return tables.written(
        "How many features of each class the filter would select", _SELECTED, rows
    )


def taken(stats: CatalogueStats, read: DatasetStats) -> widgets.Widget:
    """Tabulate how many observations of a feature of each class would be kept.

    Args:
        stats: What the catalogue index holds, which orders the classes.
        read: What the filter made of the features swept.

    Returns:
        The table as a widget, an instrument to a column since the classes are
        what it is read down.
    """
    rows = [
        (name,) + tuple(_kept(read.classes.get(name), iid) for iid in read.iids)
        for name in stats.classes
    ]
    return tables.written(
        "How many observations of a selected feature each instrument would keep",
        ("Feature class",) + tuple(read.iids),
        rows,
    )


def _kept(made: ClassStats | None, iid: str) -> str:
    """Write how many observations of a selected feature one instrument keeps.

    Args:
        made: What the filter made of the class, or None where it took none.
        iid: The instrument to write.

    Returns:
        The count, or nothing where the filter selected none of the class.
    """
    if made is None:
        return wording.NOTHING
    measured = made.taken.get(iid)
    if measured is None or not measured.counted:
        return wording.NOTHING
    return wording.spread(measured, lambda counted: f"{counted:,.0f}")

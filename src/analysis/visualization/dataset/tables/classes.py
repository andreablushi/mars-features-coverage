"""What each strategy would make of the features of each class."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import ipywidgets as widgets

from analysis.sampling.models.catalogue import CatalogueStats
from analysis.sampling.models.dataset import ClassStats, DatasetStats
from analysis.sampling.models.spread import Spread
from analysis.visualization.common import tables, wording

Read = Mapping[str, DatasetStats]


def selected(stats: CatalogueStats, read: Read) -> widgets.Widget:
    """Tabulate how many features of each class each strategy would select.

    Args:
        stats: What the catalogue index holds.
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return _per_class(
        "How many features of each class each strategy would select",
        stats,
        read,
        lambda made: f"{made.selected:,}",
    )


def taken(stats: CatalogueStats, read: Read) -> widgets.Widget:
    """Tabulate how many observations of a feature of each class would be kept.

    Args:
        stats: What the catalogue index holds.
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return _per_instrument(
        "How many observations of a selected feature each instrument would keep, "
        "by class",
        stats,
        read,
        lambda made, iid: made.taken.get(iid),
        lambda counted: f"{counted:,.0f}",
    )


def _per_class(
    title: str,
    stats: CatalogueStats,
    read: Read,
    write: Callable[[ClassStats], str],
) -> widgets.Widget:
    """Write one measurement of every feature class, a strategy per column.

    Args:
        title: The bold line above the table.
        stats: What the catalogue index holds, which orders the classes.
        read: What each strategy made of the features swept, by strategy name.
        write: How one strategy's reading of one class is put into words.

    Returns:
        The table as a widget, reading nothing where a strategy selected none
        of a class.
    """
    rows = [
        (name,)
        + tuple(
            wording.NOTHING if made is None else write(made)
            for made in (predicted.classes.get(name) for predicted in read.values())
        )
        for name in stats.classes
    ]
    return tables.written(title, ("Feature class",) + tuple(read), rows)


def _per_instrument(
    title: str,
    stats: CatalogueStats,
    read: Read,
    pick: Callable[[ClassStats, str], Spread | None],
    write: Callable[[float], str],
) -> widgets.Widget:
    """Write one measurement of every class and instrument, a strategy per column.

    Args:
        title: The bold line above the table.
        stats: What the catalogue index holds, which orders the classes.
        read: What each strategy made of the features swept, by strategy name.
        pick: The measurement to read off one class under one instrument.
        write: How one of its numbers is put into words and units.

    Returns:
        The table as a widget, reading nothing where a strategy selected none
        of a class.
    """
    iids = list(
        dict.fromkeys(iid for predicted in read.values() for iid in predicted.iids)
    )
    rows = [
        (name, iid)
        + tuple(
            _measured(predicted.classes.get(name), iid, pick, write)
            for predicted in read.values()
        )
        for name in stats.classes
        for iid in iids
    ]
    return tables.written(title, ("Feature class", "Instrument") + tuple(read), rows)


def _measured(
    made: ClassStats | None,
    iid: str,
    pick: Callable[[ClassStats, str], Spread | None],
    write: Callable[[float], str],
) -> str:
    """Write one instrument's reading of one class under one strategy.

    Args:
        made: What the strategy made of the class, or None where it took none.
        iid: The instrument to write.
        pick: The measurement to read off it.
        write: How one of its numbers is put into words and units.

    Returns:
        The measurement, or nothing where the strategy selected none of the class.
    """
    if made is None:
        return wording.NOTHING
    measured = pick(made, iid)
    if measured is None or not measured.counted:
        return wording.NOTHING
    return wording.spread(measured, write)

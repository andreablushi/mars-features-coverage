"""What the measured dataset holds before any strategy is asked of it."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import ipywidgets as widgets

from sampling.models.catalogue import CatalogueStats
from sampling.models.dataset import ClassStats, DatasetStats
from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row

_FEATURES = ("Statistic", "Value")
_INSTRUMENTS = (
    "Instrument",
    "Features reached",
    "Observations",
    "Ground reached",
    "Share of the ground",
    "First look",
    "Last look",
)
_CLASSES = ("Feature class", "Features measured", "Mean feature size")


def measured(stats: CatalogueStats) -> widgets.Widget:
    """Tabulate how big the measured dataset is.

    Args:
        stats: What the catalogue index holds.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "The ODE dataset that was measured",
        _FEATURES,
        [
            ("Features catalogued", f"{stats.catalogued:,}"),
            ("Features dropped as points", f"{stats.points:,}"),
            ("Features measured", f"{stats.features:,}"),
            ("Feature classes", f"{len(stats.classes):,}"),
            ("Ground, features summed", quantities.area(stats.area_km2)),
        ],
    )


def instruments(stats: CatalogueStats) -> widgets.Widget:
    """Tabulate what each instrument holds of the measured dataset.

    Args:
        stats: What the catalogue index holds.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "Global instrument coverage",
        _INSTRUMENTS,
        [
            (
                instrument.iid,
                f"{instrument.features:,}",
                f"{instrument.observations:,}",
                quantities.area(instrument.covered_km2),
                f"{instrument.covered_km2 / stats.area_km2:.1%}",
                instrument.first.date().isoformat(),
                instrument.last.date().isoformat(),
            )
            for instrument in stats.instruments
        ],
    )


def held(stats: CatalogueStats) -> widgets.Widget:
    """Tabulate how many features each class holds and how big they are.

    Args:
        stats: What the catalogue index holds.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "What each feature class holds",
        _CLASSES,
        [
            (name, f"{counted:,}", quantities.area(stats.class_km2[name]))
            for name, counted in stats.classes.items()
        ],
    )


def selected(stats: CatalogueStats, read: Mapping[str, DatasetStats]) -> widgets.Widget:
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


def covered(stats: CatalogueStats, read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how much of a feature of each class each strategy would hold.

    Args:
        stats: What the catalogue index holds.
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return _per_class(
        "How much of a selected feature each strategy would hold, by class",
        stats,
        read,
        lambda made: f"{made.covered:.1%}",
    )


def lasting(stats: CatalogueStats, read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate how long a window runs on a feature of each class.

    Args:
        stats: What the catalogue index holds.
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    return _per_class(
        "How long a window runs on a selected feature, by class",
        stats,
        read,
        lambda made: quantities.duration(made.days),
    )


def _per_class(
    title: str,
    stats: CatalogueStats,
    read: Mapping[str, DatasetStats],
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
    rows: list[Row] = []
    for name in stats.classes:
        made = [predicted.classes.get(name) for predicted in read.values()]
        rows.append(
            (name,)
            + tuple(wording.NOTHING if one is None else write(one) for one in made)
        )
    return tables.written(title, ("Feature class",) + tuple(read), rows)

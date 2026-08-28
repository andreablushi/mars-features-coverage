"""What the measured dataset holds before any strategy is asked of it."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import ipywidgets as widgets

from sampling.models.catalogue import CatalogueStats
from sampling.models.dataset import ClassStats, DatasetStats
from sampling.models.spread import Spread
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
_OBSERVED = "mean number of observations"


def _once(km2: float) -> str:
    """Write an amount of ground the features share nothing of.

    Args:
        km2: The ground, and nought where it could not be measured.

    Returns:
        The ground, or that it was never measured.
    """
    return quantities.area(km2) if km2 else wording.UNCOUNTED


def _share(km2: float, of_km2: float) -> str:
    """Write what share one amount of ground is of another.

    Args:
        km2: The ground reached.
        of_km2: The ground there was to reach.

    Returns:
        The share, or that it was never measured.
    """
    return f"{km2 / of_km2:.1%}" if km2 and of_km2 else wording.UNCOUNTED


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
            ("Ground, overlaps removed", _once(stats.union_km2)),
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
                _once(instrument.union_km2),
                _share(instrument.union_km2, stats.union_km2),
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
    iids = [instrument.iid for instrument in stats.instruments]
    rows: list[Row] = []
    for name, counted in stats.classes.items():
        taken = stats.class_observations.get(name, {})
        rows.append(
            (
                name,
                f"{counted:,}",
                wording.spread(stats.class_km2[name], quantities.area),
            )
            + tuple(_observed(taken.get(iid)) for iid in iids)
        )
    headings = _CLASSES + tuple(f"{iid}, {_OBSERVED}" for iid in iids)
    return tables.written("What each feature class holds", headings, rows)


def _observed(measured: Spread | None) -> str:
    """Write how many observations of a feature one instrument took.

    Args:
        measured: The count, feature by feature, or None where it reached none.

    Returns:
        The mean and its spread, or nothing at all where it reached none.
    """
    if measured is None or not measured.counted:
        return wording.NOTHING
    return wording.spread(measured, lambda counted: f"{counted:,.0f}")


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
    """Tabulate how much of a feature of each class each instrument would reach.

    Args:
        stats: What the catalogue index holds.
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    iids = list(
        dict.fromkeys(iid for predicted in read.values() for iid in predicted.iids)
    )
    rows: list[Row] = []
    # Every feature class after the first is ruled off from the one above it
    groups: list[int] = []
    for name in stats.classes:
        if rows:
            groups.append(len(rows))
        for iid in iids:
            rows.append(
                (name, iid)
                + tuple(
                    _reach(predicted.classes.get(name), iid)
                    for predicted in read.values()
                )
            )
    return tables.written(
        "How much of a selected feature each instrument would reach, by class",
        ("Feature class", "Instrument") + tuple(read),
        rows,
        groups=groups,
    )


def _reach(made: ClassStats | None, iid: str) -> str:
    """Write what one instrument reaches of a feature of one class.

    Args:
        made: What the strategy made of the class, or None where it took none.
        iid: The instrument to write.

    Returns:
        The share, or nothing at all where the strategy selected none of it.
    """
    if made is None or iid not in made.covered:
        return wording.NOTHING
    return wording.spread(made.covered[iid], lambda share: f"{share:.1%}")


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
        lambda made: wording.spread(made.days, quantities.duration),
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

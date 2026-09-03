"""What the measured dataset holds before the filter is asked of it."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.stats.models.catalogue import CatalogueStats
from analysis.utils.maths import quantities
from analysis.visualization.common import tables, wording

_FEATURES = ("Statistic", "Value")
_INSTRUMENTS = (
    "Instrument",
    "Features reached",
    "Observations",
    "Mean number of observations",
    "Ground reached",
    "Share of the ground",
    "First look",
    "Last look",
)
_CLASSES = ("Feature class", "Features measured", "Mean feature size")


def measured(stats: CatalogueStats) -> widgets.Widget:
    """Tabulate how big the measured dataset is."""
    return tables.written(
        "The ODE dataset that was measured",
        _FEATURES,
        [
            ("Features catalogued", f"{stats.catalogued:,}"),
            ("Features dropped as points", f"{stats.points:,}"),
            ("Features measured", f"{stats.features:,}"),
            ("Feature classes", f"{len(stats.classes):,}"),
            ("Ground, features summed", quantities.area(stats.area_km2)),
            ("Ground, overlaps removed", quantities.area(stats.union_km2)),
        ],
    )


def instruments(stats: CatalogueStats) -> widgets.Widget:
    """Tabulate what each instrument holds of the measured dataset."""
    return tables.written(
        "Global instrument coverage",
        _INSTRUMENTS,
        [
            (
                instrument.iid,
                f"{instrument.features:,}",
                f"{instrument.observations:,}",
                wording.spread(
                    instrument.per_feature, lambda counted: f"{counted:,.0f}"
                ),
                quantities.area(instrument.union_km2),
                f"{instrument.union_km2 / stats.union_km2:.1%}",
                instrument.first.date().isoformat(),
                instrument.last.date().isoformat(),
            )
            for instrument in stats.instruments
        ],
    )


def held(stats: CatalogueStats) -> widgets.Widget:
    """Tabulate how many features each class holds and how big they are."""
    return tables.written(
        "What each feature class holds",
        _CLASSES,
        [
            (
                name,
                f"{counted:,}",
                wording.spread(stats.class_km2[name], quantities.area),
            )
            for name, counted in stats.classes.items()
        ],
    )

"""What the measured dataset holds before any strategy is asked of it."""

from __future__ import annotations

import ipywidgets as widgets

from sampling.models.catalogue import CatalogueStats, InstrumentStats
from utils.maths import quantities
from visualization.common import tables
from visualization.common.tables import Row

_FEATURES = ("Statistic", "Value")
_POINTS = (
    "A feature the catalogue gives no extent at all is a point on the map, so there "
    "is no ground to crop an observation to and it is dropped before any download."
)
_CLASSES = ("Feature class", "Features kept", "Share of the features")
_INSTRUMENTS = (
    "Instrument",
    "Features reached",
    "Observations",
    "Ground reached",
    "Share of the ground",
    "First look",
    "Last look",
)


def measured(stats: CatalogueStats) -> widgets.Widget:
    """Tabulate how big the measured dataset is.

    Args:
        stats: What the catalogue index holds.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "The dataset that was measured",
        _FEATURES,
        [
            ("Features", f"{stats.features:,}"),
            ("Feature classes", f"{len(stats.classes):,}"),
            ("Features dropped as points", f"{stats.points:,}"),
            ("Ground", quantities.area(stats.area_km2)),
            ("Tiles", f"{stats.tiles:,}"),
        ],
        note=_POINTS,
    )


def classes(stats: CatalogueStats) -> widgets.Widget:
    """Tabulate how many features of each class the measurement kept.

    Args:
        stats: What the catalogue index holds.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "How many features of each class were kept",
        _CLASSES,
        [
            (name, f"{counted:,}", f"{counted / stats.features:.1%}")
            for name, counted in stats.classes.items()
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
        "What each instrument holds",
        _INSTRUMENTS,
        [_held(instrument, stats.area_km2) for instrument in stats.instruments],
    )


def _held(instrument: InstrumentStats, area_km2: float) -> Row:
    """Write one instrument's row.

    Args:
        instrument: What it holds of the dataset.
        area_km2: The ground every measured feature holds between them.

    Returns:
        The row.
    """
    return (
        instrument.iid,
        f"{instrument.features:,}",
        f"{instrument.observations:,}",
        quantities.area(instrument.covered_km2),
        f"{instrument.covered_km2 / area_km2:.1%}",
        instrument.first.date().isoformat(),
        instrument.last.date().isoformat(),
    )

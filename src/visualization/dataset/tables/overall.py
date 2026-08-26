"""What the measured dataset holds before any strategy is asked of it."""

from __future__ import annotations

import ipywidgets as widgets

from prediction.stats.catalogue import CatalogueStats, Held
from utils.maths import quantities
from visualization.common import tables, wording
from visualization.common.tables import Row

_FEATURES = ("Statistic", "Value")
_INSTRUMENTS = (
    "Instrument",
    "Features reached",
    "Observations",
    "Pixels",
    "Ground reached",
    "First look",
    "Last look",
    "Record of a feature",
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
            ("Feature classes", f"{stats.classes:,}"),
            ("Ground", quantities.area(stats.area_km2)),
            ("Grid cells", f"{stats.cells:,}"),
            ("Tiles", f"{stats.tiles:,}"),
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
        [_held(instrument) for instrument in stats.instruments],
    )


def _held(instrument: Held) -> Row:
    """Write one instrument's row.

    Args:
        instrument: What it holds of the dataset.

    Returns:
        The row.
    """
    spans = instrument.spans
    return (
        instrument.iid,
        f"{instrument.features:,}",
        f"{instrument.observations:,}",
        wording.pixels(instrument.pixels),
        quantities.area(instrument.covered_km2),
        instrument.first.date().isoformat(),
        instrument.last.date().isoformat(),
        f"{quantities.duration(spans.mean)} ± {quantities.duration(spans.deviation)}",
    )

"""The measured dataset read as one, before any strategy is asked of it."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from models.results import Summary
from storage import summary as index
from visualization.common import spread
from visualization.common.spread import Spread


@dataclass(frozen=True, slots=True)
class Held:
    """What one instrument holds of the whole measured dataset.

    Attributes:
        iid: The instrument, such as CTX.
        features: How many features it reached.
        observations: How many observations of them it took.
        pixels: How many of its pixels landed inside them.
        covered_km2: How much of their ground it reached.
        first: When the earliest of its observations was taken.
        last: When the latest of them was taken.
        spans: How long its record of one feature runs, in days, feature by
            feature.
    """

    iid: str
    features: int
    observations: int
    pixels: float
    covered_km2: float
    first: datetime
    last: datetime
    spans: Spread


@dataclass(frozen=True, slots=True)
class CatalogueStats:
    """What the measured dataset holds, whatever a strategy would make of it.

    Attributes:
        features: How many features were measured.
        classes: How many feature classes they belong to.
        area_km2: How much ground their bounding boxes cover between them.
        cells: How many grid cells of them the measurement laid down.
        tiles: How many tiles the measurement cut them into between them.
        instruments: What each instrument holds, most observations first.
    """

    features: int
    classes: int
    area_km2: float
    cells: int
    tiles: int
    instruments: list[Held]


def read() -> CatalogueStats:
    """Read the catalogue index as one dataset.

    Returns:
        What it holds, and nothing at all when no feature was measured.
    """
    rows = index.catalogued_rows()
    # One row per feature carries the grid, which every set of it shares
    features: dict[tuple[str, str], Summary] = {}
    for row in rows:
        features.setdefault((row.feature_class, row.feature_name), row)
    return CatalogueStats(
        features=len(features),
        classes=len({feature_class for feature_class, _ in features}),
        area_km2=sum(row.feature_area_km2 for row in features.values()),
        cells=sum(row.mask_cells for row in features.values()),
        tiles=sum(row.tiles_across**2 for row in features.values()),
        instruments=_instruments(rows),
    )


def _instruments(rows: Sequence[Summary]) -> list[Held]:
    """Read what each instrument holds of the dataset.

    Args:
        rows: Every row of the catalogue index.

    Returns:
        One entry per instrument, most observations first.
    """
    grouped: dict[str, list[Summary]] = {}
    for row in rows:
        grouped.setdefault(row.iid, []).append(row)
    held = [
        Held(
            iid=iid,
            features=len({(row.feature_class, row.feature_name) for row in taken}),
            observations=sum(row.n_obs for row in taken),
            pixels=sum(row.pixels for row in taken),
            covered_km2=sum(row.covered_km2 for row in taken),
            first=min(row.t_first for row in taken),
            last=max(row.t_last for row in taken),
            spans=spread.over([row.span_days for row in taken]),
        )
        for iid, taken in grouped.items()
    ]
    return sorted(held, key=lambda instrument: -instrument.observations)

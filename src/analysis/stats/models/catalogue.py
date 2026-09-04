"""What the measured dataset holds, before the filter is asked of it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from analysis.stats.models.spread import Spread


@dataclass(frozen=True, slots=True)
class InstrumentStats:
    """What one instrument holds of the whole measured dataset.

    Attributes:
        iid: The instrument, such as CTX.
        features: How many features it reached.
        observations: How many observations of them it took.
        first: When the earliest of its observations was taken.
        last: When the latest of them was taken.
    """

    iid: str
    features: int
    observations: int
    first: datetime
    last: datetime


@dataclass(frozen=True, slots=True)
class CatalogueStats:
    """What the measured dataset holds, whatever the filter would make of it.

    Attributes:
        catalogued: How many features the ODE catalogue holds altogether.
        features: How many of them were measured.
        points: How many the catalogue gives no extent, so none could be measured.
        classes: How many features each class holds, most features first.
        class_km2: How much ground a feature of each class holds, feature by
            feature, by class.
        instruments: What each instrument holds, most observations first.
    """

    catalogued: int
    features: int
    points: int
    classes: dict[str, int]
    class_km2: dict[str, Spread]
    instruments: list[InstrumentStats]

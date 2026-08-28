"""What the measured dataset holds, before any strategy is asked of it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sampling.models.spread import Spread


@dataclass(frozen=True, slots=True)
class Reach:
    """What one instrument reached of one feature.

    Attributes:
        area_km2: The ground the feature's bounding box holds.
        covered_frac: The share of that ground the instrument reached.
        pixels_per_observation: The pixels one of its observations landed there.
    """

    area_km2: float
    covered_frac: float
    pixels_per_observation: float


@dataclass(frozen=True, slots=True)
class InstrumentStats:
    """What one instrument holds of the whole measured dataset.

    Attributes:
        iid: The instrument, such as CTX.
        features: How many features it reached.
        observations: How many observations of them it took.
        covered_km2: How much of their ground it reached, counting ground two
            overlapping features share once per feature.
        union_km2: The same, counting that shared ground once in all, and nought
            where the observations it was read from are not on disk.
        first: When the earliest of its observations was taken.
        last: When the latest of them was taken.
        reach: What it reached of each feature it reached, one entry each.
    """

    iid: str
    features: int
    observations: int
    covered_km2: float
    union_km2: float
    first: datetime
    last: datetime
    reach: list[Reach]


@dataclass(frozen=True, slots=True)
class CatalogueStats:
    """What the measured dataset holds, whatever a strategy would make of it.

    Attributes:
        catalogued: How many features the ODE catalogue holds altogether.
        features: How many of them were measured.
        points: How many the catalogue gives no extent, so none could be measured.
        classes: How many features each class holds, most features first.
        class_km2: How much ground a feature of each class holds, feature by
            feature, by class.
        area_km2: How much ground their bounding boxes cover between them,
            counting ground two overlapping features share once per feature.
        union_km2: The same, counting that shared ground once in all, and nought
            where it could not be measured.
        instruments: What each instrument holds, most observations first.
    """

    catalogued: int
    features: int
    points: int
    classes: dict[str, int]
    class_km2: dict[str, Spread]
    area_km2: float
    union_km2: float
    instruments: list[InstrumentStats]

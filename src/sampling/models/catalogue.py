"""What the measured dataset holds, before any strategy is asked of it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class InstrumentStats:
    """What one instrument holds of the whole measured dataset.

    Attributes:
        iid: The instrument, such as CTX.
        features: How many features it reached.
        observations: How many observations of them it took.
        pixels: How many of its pixels landed inside them.
        covered_km2: How much of their ground it reached.
        first: When the earliest of its observations was taken.
        last: When the latest of them was taken.
    """

    iid: str
    features: int
    observations: int
    pixels: float
    covered_km2: float
    first: datetime
    last: datetime


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
    instruments: list[InstrumentStats]

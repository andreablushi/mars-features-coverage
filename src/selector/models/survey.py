"""The stretch of time the search picked."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Survey:
    """The stretch of time one tile of a feature is best studied over.

    Attributes:
        tile: Which tile of the feature it was found over.
        area_km2: How much ground that tile covers.
        start: When the earliest observation inside it was taken.
        end: When the latest one was taken.
        days: How long it lasts.
        geo_mean: The insisted shares rooted together, as a share of the tile.
        kept: The observations it holds, as their places on the timeline, oldest first.
        dropped: How many were dropped from it as repeats of ground it already held.
        standing: The observations kept from outside the window, oldest first.
    """

    tile: int
    area_km2: float
    start: datetime
    end: datetime
    days: float
    geo_mean: float
    kept: tuple[int, ...]
    dropped: int
    standing: tuple[int, ...]

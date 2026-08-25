"""The stretch of time the search picked."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Survey:
    """The stretch of time one tile of a feature is best studied over.

    Attributes:
        tile: Which tile of the feature it was found over.
        area_km2: How much ground that tile covers, which is what the dataset
            gains by keeping the window.
        start: When the earliest observation inside it was taken.
        end: When the latest one was taken.
        days: How long it lasts.
        reach: How much of the tile it reaches, as the shares each instrument
            insisted on reaches of it, multiplied and rooted so that one
            instrument cannot carry the window alone, and counting one that
            never appears as nothing.
        kept: The observations it holds, as their places on the timeline,
            oldest first. Every one of them brought ground no other
            observation of its own set reaches, so these are what the tile
            would put in a dataset.
        dropped: How many were dropped from it as repeats of ground it already
            held.
        standing: The observations kept from outside the window, as their
            places on the timeline, oldest first. A timeless instrument is
            asked of the whole record rather than of the window, so what it
            brought the tile is kept wherever on the axis it flew.
    """

    tile: int
    area_km2: float
    start: datetime
    end: datetime
    days: float
    reach: float
    kept: tuple[int, ...]
    dropped: int
    standing: tuple[int, ...]

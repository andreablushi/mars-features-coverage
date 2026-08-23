"""The stretch of time the search picked."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Survey:
    """The stretch of time one tile of a feature is best studied over.

    Attributes:
        tile: Which tile of the feature it was found over.
        start: When the earliest observation inside it was taken.
        end: When the latest one was taken.
        days: How long it lasts.
        reach: How much of the tile it reaches, as the shares each instrument
            insisted on reaches of it, multiplied and rooted so that one
            instrument cannot carry the window alone, and counting one that
            never appears as nothing.
        instruments: How many sets have an observation inside it.
        observations: How many observations it holds in total.
        core: How many of them brought ground nothing before them in the window
            had already brought.
        knee: Whether the curve bent, and the window is the bend in it, rather
            than the longest window the curve reached.
    """

    tile: int
    start: datetime
    end: datetime
    days: float
    reach: float
    instruments: int
    observations: int
    core: int
    knee: bool

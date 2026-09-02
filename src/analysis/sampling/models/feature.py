"""What one feature holds, and what a run of features holds as one."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from analysis.sampling.models.spread import Spread


@dataclass(frozen=True, slots=True)
class InstrumentReach:
    """What one instrument left on one feature inside its window.

    Attributes:
        km2: The ground it reaches, counting a cell once however often it was revisited.
        pixels: The pixels it landed there, or None where any carries no count.
        observations_taken: How many of its observations the window keeps.
    """

    km2: float
    pixels: float | None
    observations_taken: int


@dataclass(frozen=True, slots=True)
class FeatureStats:
    """One feature, and what the search left on it.

    Attributes:
        area_km2: How much ground it covers.
        kept: Whether it earned a window worth keeping.
        start: When the earliest observation in its window was taken, or None.
        end: When the latest one was taken, or None when it earned none.
        days: How long its window lasts.
        geo_mean: The geometric mean its window scores, as the search computes it.
        taken: How many observations it keeps, from the window and outside it.
        dropped: How many the window dropped as repeats of ground it held.
        refused: How many looks fell inside the window but were too small for it.
        turned_away: How many looks were too small for the feature at all.
        offered: How many observations of each instrument landed on it at all.
        pixel_km2: The ground one pixel of each instrument covers, read off the
            observations offered to the feature rather than off the ones a window kept.
        reached: What each instrument left on it, by instrument.
        overlaps: The ground each set of instruments reaches, most ground first.
    """

    area_km2: float
    kept: bool
    start: datetime | None
    end: datetime | None
    days: float
    geo_mean: float
    taken: int
    dropped: int
    refused: int
    turned_away: int
    offered: dict[str, int]
    pixel_km2: dict[str, float]
    reached: dict[str, InstrumentReach]
    overlaps: dict[tuple[str, ...], float]


@dataclass(frozen=True, slots=True)
class Aggregate:
    """What a run of features holds between them.

    Attributes:
        searched: How many features the search ran over.
        kept: How many of them earned a window worth keeping.
        area_km2: How much ground those searched features hold.
        kept_km2: How much of it the kept ones hold.
        days: How long the windows last, over the kept features.
        geo_mean: The geometric mean its window scores, over the kept features.
        reached: The share of a feature each instrument reaches, over the kept.
        landed: The pixels each instrument landed on a feature, over the kept.
        pixels_per_look: The pixels one observation of each instrument landed on
            a feature, over the kept features it took any of.
        pixel_km2: The ground one pixel of each instrument covers, over every
            feature searched, since an instrument's pixel is the same size
            whichever feature it falls on and whether or not it earned a window.
        overlaps: The ground each set of instruments reaches, most ground first.
    """

    searched: int
    kept: int
    area_km2: float
    kept_km2: float
    days: Spread
    geo_mean: Spread
    reached: dict[str, Spread]
    landed: dict[str, Spread]
    pixels_per_look: dict[str, Spread]
    pixel_km2: dict[str, Spread]
    overlaps: dict[tuple[str, ...], float]

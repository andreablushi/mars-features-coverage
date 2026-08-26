"""Many tiles read as one, whether they belong to a feature or to a dataset."""

from __future__ import annotations

from dataclasses import dataclass

from sampling.models.spread import Spread


@dataclass(frozen=True, slots=True)
class Aggregate:
    """What a run of tiles holds between them.

    Attributes:
        searched: How many tiles the search ran over.
        kept: How many of them earned a window worth keeping.
        area_km2: How much ground those searched tiles hold.
        kept_km2: How much of it the kept ones hold.
        days: How long the windows last, over the kept tiles.
        geo_mean: The geometric mean its window scores, over the kept tiles.
        reached: The share of a tile each instrument reaches, over the kept tiles.
        landed: The pixels each instrument landed on a tile, over the kept tiles.
        pixel_km2: The ground one pixel of each instrument covers, over them.
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
    pixel_km2: dict[str, Spread]
    overlaps: dict[tuple[str, ...], float]

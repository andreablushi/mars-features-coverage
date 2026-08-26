"""What one tile of a feature holds, read off the search that ran over it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Reach:
    """What one instrument left on one tile inside its window.

    Attributes:
        km2: The ground it reaches, counting a cell once however often it was revisited.
        pixels: The pixels it landed there, or None where any carries no count.
        taken: How many of its observations the window keeps.
    """

    km2: float
    pixels: float | None
    taken: int


@dataclass(frozen=True, slots=True)
class TileStats:
    """One tile of a feature, and what the search left on it.

    Attributes:
        tile: Which tile of the feature it is, as the grid numbers them.
        row: Which row of the grid it sits in, counting north from the south edge.
        column: Which column it sits in, counting east from the west edge.
        area_km2: How much of the feature it holds.
        kept: Whether it earned a window worth keeping.
        start: When the earliest observation in its window was taken, or None.
        end: When the latest one was taken, or None when it earned none.
        days: How long its window lasts.
        geo_mean: The geometric mean its window scores, as the search computes it.
        taken: How many observations the tile keeps, from the window and outside it.
        dropped: How many the window dropped as repeats of ground it held.
        refused: How many looks fell inside the window but were too small for the tile.
        turned_away: How many looks were too small for the tile at all.
        offered: How many observations of each instrument landed on the tile at all.
        reached: What each instrument left on the tile, by instrument.
        overlaps: The ground each set of instruments reaches, most ground first.
    """

    tile: int
    row: int
    column: int
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
    reached: dict[str, Reach]
    overlaps: dict[tuple[str, ...], float]

"""Many tiles read as one, whether they belong to a feature or to a dataset."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from visualization.common import spread
from visualization.common.spread import Spread
from visualization.common.tiles import TileStats


@dataclass(frozen=True, slots=True)
class Aggregate:
    """What a run of tiles holds between them.

    Attributes:
        searched: How many tiles the search ran over.
        kept: How many of them earned a window worth keeping.
        area_km2: How much ground those searched tiles hold.
        kept_km2: How much of it the kept ones hold.
        days: How long the windows last, over the kept tiles.
        reach: How much of a tile its window reaches, over the kept tiles.
        taken: How many observations the windows keep between them.
        dropped: How many they dropped as repeats of ground already held.
        refused: How many looks fell inside a window but were too small for
            the tile.
        turned_away: How many looks were too small for the tile at all.
        reached: The share of a tile each instrument reaches, over the kept
            tiles, counting a tile it never appears on as nothing.
        pixels: The pixels each instrument landed inside the windows, or None
            for one whose observations carry no pixel count.
        overlaps: How much ground each set of instruments reaches between
            them, by the instruments really there, most ground first.
    """

    searched: int
    kept: int
    area_km2: float
    kept_km2: float
    days: Spread
    reach: Spread
    taken: int
    dropped: int
    refused: int
    turned_away: int
    reached: dict[str, Spread]
    pixels: dict[str, float | None]
    overlaps: dict[tuple[str, ...], float]


def over(measured: Sequence[TileStats], iids: Sequence[str]) -> Aggregate:
    """Read a run of tiles as one.

    Args:
        measured: The tiles the search ran over, in any order.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What they hold between them.
    """
    held = [tile for tile in measured if tile.kept]
    return Aggregate(
        searched=len(measured),
        kept=len(held),
        area_km2=sum(tile.area_km2 for tile in measured),
        kept_km2=sum(tile.area_km2 for tile in held),
        days=spread.over([tile.days for tile in held]),
        reach=spread.over([tile.reach for tile in held]),
        taken=sum(tile.taken for tile in measured),
        dropped=sum(tile.dropped for tile in measured),
        refused=sum(tile.refused for tile in measured),
        turned_away=sum(tile.turned_away for tile in measured),
        reached={iid: _reached(held, iid) for iid in iids},
        pixels={iid: _pixels(held, iid) for iid in iids},
        overlaps=_overlaps(held),
    )


def _reached(held: Sequence[TileStats], iid: str) -> Spread:
    """Read how much of a tile one instrument reaches, tile by tile.

    Args:
        held: The tiles that earned a window.
        iid: The instrument to read.

    Returns:
        The share of a tile it reaches, counting a tile whose window it never
        appears in as nothing.
    """
    return spread.over(
        [
            tile.reached[iid].km2 / tile.area_km2 if iid in tile.reached else 0.0
            for tile in held
            if tile.area_km2
        ]
    )


def _pixels(held: Sequence[TileStats], iid: str) -> float | None:
    """Add up the pixels one instrument landed inside the windows.

    Args:
        held: The tiles that earned a window.
        iid: The instrument to count.

    Returns:
        The pixels, or None when any tile carries no count for it.
    """
    total = 0.0
    for tile in held:
        reach = tile.reached.get(iid)
        if reach is None:
            continue
        if reach.pixels is None:
            return None
        total += reach.pixels
    return total


def _overlaps(held: Sequence[TileStats]) -> dict[tuple[str, ...], float]:
    """Add up the ground each set of instruments reaches between them.

    Args:
        held: The tiles that earned a window, whose grounds are disjoint and
            so add up.

    Returns:
        The ground in square kilometres, by the instruments that reach it,
        most ground first.
    """
    merged: dict[tuple[str, ...], float] = {}
    for tile in held:
        for names, km2 in tile.overlaps.items():
            merged[names] = merged.get(names, 0.0) + km2
    return dict(sorted(merged.items(), key=lambda ground: -ground[1]))

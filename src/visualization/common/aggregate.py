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
        reached: The share of a tile each instrument reaches, over the kept tiles.
        landed: The pixels each instrument landed on a tile, over the kept tiles.
        overlaps: The ground each set of instruments reaches, most ground first.
    """

    searched: int
    kept: int
    area_km2: float
    kept_km2: float
    days: Spread
    reach: Spread
    reached: dict[str, Spread]
    landed: dict[str, Spread]
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
        reached={iid: _reached(held, iid) for iid in iids},
        landed={iid: _landed(held, iid) for iid in iids},
        overlaps=_overlaps(held),
    )


def _reached(held: Sequence[TileStats], iid: str) -> Spread:
    """Read how much of a tile one instrument reaches, tile by tile.

    Args:
        held: The tiles that earned a window.
        iid: The instrument to read.

    Returns:
        The share of a tile it reaches, counting one it never appears in as nothing.
    """
    return spread.over(
        [
            tile.reached[iid].km2 / tile.area_km2 if iid in tile.reached else 0.0
            for tile in held
            if tile.area_km2
        ]
    )


def _landed(held: Sequence[TileStats], iid: str) -> Spread:
    """Read how many pixels one instrument lands on a tile, tile by tile.

    Args:
        held: The tiles that earned a window.
        iid: The instrument to read.

    Returns:
        The pixels it lands on a tile, and empty when any tile carries no count.
    """
    counted: list[float] = []
    for tile in held:
        reach = tile.reached.get(iid)
        if reach is None:
            counted.append(0.0)
        elif reach.pixels is None:
            return spread.over([])
        else:
            counted.append(reach.pixels)
    return spread.over(counted)


def _overlaps(held: Sequence[TileStats]) -> dict[tuple[str, ...], float]:
    """Add up the ground each set of instruments reaches between them.

    Args:
        held: The tiles that earned a window, whose grounds are disjoint and so add up.

    Returns:
        The ground in square kilometres, by the instruments reaching it.
    """
    merged: dict[tuple[str, ...], float] = {}
    for tile in held:
        for names, km2 in tile.overlaps.items():
            merged[names] = merged.get(names, 0.0) + km2
    return dict(sorted(merged.items(), key=lambda ground: -ground[1]))

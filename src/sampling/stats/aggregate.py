"""Reading a run of tiles as one, whatever feature or dataset they belong to."""

from __future__ import annotations

from collections.abc import Sequence

from sampling.models.aggregate import Aggregate
from sampling.models.spread import Spread
from sampling.models.tiles import TileStats


def over(measured: Sequence[TileStats], iids: Sequence[str]) -> Aggregate:
    """Read a run of tiles as one.

    Args:
        measured: The tiles the search ran over, in any order.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What they hold between them.
    """
    held = [tile for tile in measured if tile.kept]
    # The grounds of the kept tiles are disjoint, so their overlaps add up
    overlaps: dict[tuple[str, ...], float] = {}
    for tile in held:
        for names, km2 in tile.overlaps.items():
            overlaps[names] = overlaps.get(names, 0.0) + km2
    return Aggregate(
        searched=len(measured),
        kept=len(held),
        area_km2=sum(tile.area_km2 for tile in measured),
        kept_km2=sum(tile.area_km2 for tile in held),
        days=Spread.over([tile.days for tile in held]),
        geo_mean=Spread.over([tile.geo_mean for tile in held]),
        per_observation={iid: _per_observation(held, iid) for iid in iids},
        reached={
            iid: Spread.over(
                [
                    tile.reached[iid].km2 / tile.area_km2
                    if iid in tile.reached
                    else 0.0
                    for tile in held
                    if tile.area_km2
                ]
            )
            for iid in iids
        },
        landed={iid: _landed(held, iid) for iid in iids},
        pixel_km2={
            iid: Spread.over(
                [
                    tile.reached[iid].pixel_km2
                    for tile in held
                    if iid in tile.reached and tile.reached[iid].pixel_km2
                ]
            )
            for iid in iids
        },
        overlaps=dict(sorted(overlaps.items(), key=lambda ground: -ground[1])),
    )


def per_observation(shares: Sequence[float], taken: Sequence[int]) -> float:
    """Average a share over the observations that reached it, not over the tiles.

    Args:
        shares: The share one tile reached, tile by tile.
        taken: How many observations reached it there, in the same order.

    Returns:
        The share the mean observation sits on, and nought where none was taken.
    """
    counted = sum(taken)
    if not counted:
        return 0.0
    held = zip(shares, taken, strict=True)
    return sum(share * counted_here for share, counted_here in held) / counted


def _per_observation(held: Sequence[TileStats], iid: str) -> float:
    """Read the share one instrument reaches, averaged over its own observations.

    Args:
        held: The tiles that earned a window.
        iid: The instrument to read.

    Returns:
        The share of a tile the mean observation of it sits on.
    """
    shares: list[float] = []
    taken: list[int] = []
    for tile in held:
        if not tile.area_km2:
            continue
        reach = tile.reached.get(iid)
        shares.append(reach.km2 / tile.area_km2 if reach else 0.0)
        taken.append(reach.taken if reach else 0)
    return per_observation(shares, taken)


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
            return Spread.over([])
        else:
            counted.append(reach.pixels)
    return Spread.over(counted)

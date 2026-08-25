"""Every feature of the dataset read as one, under one strategy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from visualization.common import aggregate, spread, tiles
from visualization.common.aggregate import Aggregate
from visualization.common.spread import Spread
from visualization.dataset.loading import Searched

# The shares of a tile the bands count the kept tiles reaching, loosest first.
BANDS = (0.5, 0.75, 0.9)


@dataclass(frozen=True, slots=True)
class DatasetStats:
    """What one strategy would make of every feature searched.

    Attributes:
        strategy: The strategy the features were searched under.
        features: How many features were searched.
        held: Every tile of every feature, read as one.
        sizes: How much ground a tile holds, over the tiles searched.
        offered: How many observations each instrument landed on a tile, over
            the tiles searched, counting a tile it never reached as nothing.
        shared: The share of a tile exactly so many instruments reach between
            them, over the tiles kept, by how many of them reach it. A cell
            counts once, so the shares do not overlap and add up to what the
            window reaches.
        reaching: How many kept tiles hold at least so many instruments, by
            how many of them the tile holds.
        covered: How many kept tiles have at least that share of their ground
            reached by two instruments at once, by the share asked.
        iids: The instruments reported on, in the order they are drawn.
    """

    strategy: str
    features: int
    held: Aggregate
    sizes: Spread
    offered: dict[str, Spread]
    shared: dict[int, Spread]
    reaching: dict[int, int]
    covered: dict[float, int]
    iids: list[str]


def read(found: Sequence[Searched]) -> dict[str, DatasetStats]:
    """Read every strategy off one sweep of the features.

    Args:
        found: What the sweep left, one entry per feature and strategy.

    Returns:
        What each strategy would make of them, by strategy name, in the order
        the sweep first mentions each.
    """
    grouped: dict[str, list[Searched]] = {}
    for searched in found:
        grouped.setdefault(searched.strategy, []).append(searched)
    return {name: _under(name, held) for name, held in grouped.items()}


def _under(strategy: str, held: Sequence[Searched]) -> DatasetStats:
    """Read every feature searched under one strategy.

    Args:
        strategy: The strategy's name.
        held: What the sweep left of each feature under it.

    Returns:
        What the strategy would make of them.
    """
    iids = list(dict.fromkeys(iid for searched in held for iid in searched.iids))
    measured = [tile for searched in held for tile in searched.measured]
    # The kept tiles carrying ground, and how much of each so many instruments reach
    grounded = [tile for tile in measured if tile.kept and tile.area_km2]
    overlapping = [tiles.shared(tile.overlaps) for tile in grounded]
    # The share of each of those tiles two instruments or more reach at once
    together = [
        sum(km2 for counted, km2 in found.items() if counted > 1) / tile.area_km2
        for tile, found in zip(grounded, overlapping, strict=True)
    ]
    return DatasetStats(
        strategy=strategy,
        features=len(held),
        held=aggregate.over(measured, iids),
        sizes=spread.over([tile.area_km2 for tile in measured]),
        offered={
            iid: spread.over([tile.offered.get(iid, 0) for tile in measured])
            for iid in iids
        },
        shared={
            counted: spread.over(
                [
                    found.get(counted, 0.0) / tile.area_km2
                    for tile, found in zip(grounded, overlapping, strict=True)
                ]
            )
            for counted in range(1, len(iids) + 1)
        },
        reaching={
            counted: sum(1 for tile in grounded if len(tile.reached) >= counted)
            for counted in range(1, len(iids) + 1)
        },
        covered={band: sum(1 for share in together if share >= band) for band in BANDS},
        iids=iids,
    )

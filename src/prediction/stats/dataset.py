"""Every feature of the dataset read as one, under one strategy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from prediction.models import aggregate, spread, tiles
from prediction.models.aggregate import Aggregate
from prediction.models.searched import Searched
from prediction.models.spread import Spread
from prediction.models.tiles import TileStats

# How far past the whole tile a share may read before the tile is refused.
CEILING = 1.01


@dataclass(frozen=True, slots=True)
class DatasetStats:
    """What one strategy would make of every feature searched.

    Attributes:
        strategy: The strategy the features were searched under.
        features: How many features were searched.
        held: Every tile of every feature, read as one.
        sizes: How much ground a tile holds, over the tiles searched.
        offered: How many observations each instrument landed on a tile searched.
        overlap: The share of a tile every instrument reaches at once, over the kept.
        iids: The instruments reported on, in the order they are drawn.
    """

    strategy: str
    features: int
    held: Aggregate
    sizes: Spread
    offered: dict[str, Spread]
    overlap: Spread
    iids: list[str]


def read(found: Sequence[Searched]) -> dict[str, DatasetStats]:
    """Read every strategy off one sweep of the features.

    Args:
        found: What the sweep left, one entry per feature and strategy.

    Returns:
        What each strategy would make of them, by name, in the order swept.
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
    measured = [tile for searched in held for tile in searched.measured if _sound(tile)]
    # The kept tiles carrying ground, and the ground each set of instruments reaches
    grounded = [tile for tile in measured if tile.kept and tile.area_km2]
    overlapping = [tiles.shared(tile.overlaps) for tile in grounded]
    return DatasetStats(
        strategy=strategy,
        features=len(held),
        held=aggregate.over(measured, iids),
        sizes=spread.over([tile.area_km2 for tile in measured]),
        offered={
            iid: spread.over([tile.offered.get(iid, 0) for tile in measured])
            for iid in iids
        },
        overlap=spread.over(
            [
                found.get(len(iids), 0.0) / tile.area_km2
                for tile, found in zip(grounded, overlapping, strict=True)
            ]
        ),
        iids=iids,
    )


def _sound(tile: TileStats) -> bool:
    """Say whether a tile reports no more ground than it holds.

    Args:
        tile: One tile the search ran over.

    Returns:
        Whether every share it reports sits inside the ceiling.
    """
    if not tile.area_km2:
        return True
    shares = [reach.km2 / tile.area_km2 for reach in tile.reached.values()]
    shares.append(sum(tile.overlaps.values()) / tile.area_km2)
    shares.append(tile.reach)
    return max(shares) <= CEILING

"""Every feature of the dataset read as one, under one strategy."""

from __future__ import annotations

from collections.abc import Sequence

from prediction.models.dataset import DatasetStats
from prediction.models.searched import Searched
from prediction.models.spread import Spread
from prediction.models.tiles import TileStats
from prediction.stats import aggregate, tiles

# How far past the whole tile a share may read before the tile is refused.
CEILING = 1.01


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
    read_back: dict[str, DatasetStats] = {}
    for strategy, held in grouped.items():
        iids = list(dict.fromkeys(iid for searched in held for iid in searched.iids))
        measured = [
            tile for searched in held for tile in searched.measured if _sound(tile)
        ]
        # The kept tiles carrying ground, and the ground each set of instruments reaches
        grounded = [tile for tile in measured if tile.kept and tile.area_km2]
        overlapping = [tiles.shared(tile.overlaps) for tile in grounded]
        read_back[strategy] = DatasetStats(
            strategy=strategy,
            features=len(held),
            held=aggregate.over(measured, iids),
            sizes=Spread.over([tile.area_km2 for tile in measured]),
            offered={
                iid: Spread.over([tile.offered.get(iid, 0) for tile in measured])
                for iid in iids
            },
            overlap=Spread.over(
                [
                    found_here.get(len(iids), 0.0) / tile.area_km2
                    for tile, found_here in zip(grounded, overlapping, strict=True)
                ]
            ),
            iids=iids,
        )
    return read_back


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
    shares.append(tile.geo_mean)
    return max(shares) <= CEILING

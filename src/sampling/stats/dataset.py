"""Every feature of the dataset read as one, under one strategy."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from sampling.models.dataset import ClassStats, DatasetStats
from sampling.models.searched import Searched
from sampling.models.spread import Spread
from sampling.models.tiles import TileStats
from sampling.stats import aggregate, tiles

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
        # The kept tiles carrying ground, and the ground every instrument shares
        grounded = [tile for tile in measured if tile.kept and tile.area_km2]
        shared = [
            tiles.shared(tile.overlaps).get(len(iids), 0.0) / tile.area_km2
            for tile in grounded
        ]
        read_back[strategy] = DatasetStats(
            strategy=strategy,
            features=len(held),
            classes=_classes(held, iids),
            held=aggregate.over(measured, iids),
            widths=Spread.over([math.sqrt(tile.area_km2) for tile in measured]),
            offered={
                iid: Spread.over([tile.offered.get(iid, 0) for tile in measured])
                for iid in iids
            },
            overlap=Spread.over(shared),
            iids=iids,
        )
    return read_back


def _classes(held: Sequence[Searched], iids: Sequence[str]) -> dict[str, ClassStats]:
    """Read what a strategy made of the features of each class.

    Only the features it selected are averaged, since a feature it refused
    outright would otherwise drag the class down to nothing.

    Args:
        held: What the sweep left of every feature searched under it.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What it made of each class, by feature class, in the order swept.
    """
    covered: dict[str, dict[str, list[float]]] = {}
    taken: dict[str, dict[str, list[float]]] = {}
    days: dict[str, list[float]] = {}
    for searched in held:
        sound = [tile for tile in searched.measured if _sound(tile) and tile.area_km2]
        kept = [tile for tile in sound if tile.kept]
        if not kept:
            continue
        name = searched.feature_class
        reached = covered.setdefault(name, {iid: [] for iid in iids})
        counted = taken.setdefault(name, {iid: [] for iid in iids})
        for iid in iids:
            reached[iid].append(statistics.fmean(_shares(sound, iid)))
            counted[iid].append(
                sum(tile.reached[iid].taken for tile in kept if iid in tile.reached)
            )
        days.setdefault(name, []).append(statistics.fmean(tile.days for tile in kept))
    return {
        name: ClassStats(
            selected=len(days[name]),
            covered={iid: Spread.over(shares) for iid, shares in reached.items()},
            taken={iid: Spread.over(counts) for iid, counts in taken[name].items()},
            days=Spread.over(days[name]),
        )
        for name, reached in covered.items()
    }


def _shares(sound: Sequence[TileStats], iid: str) -> list[float]:
    """Read the share of each tile of one feature one instrument reaches.

    Args:
        sound: The tiles of the feature the search ran over, each holding ground.
        iid: The instrument to read.

    Returns:
        The share it reaches on each tile, nought where the tile earned no
        window or the instrument left nothing on it.
    """
    return [
        tile.reached[iid].km2 / tile.area_km2
        if tile.kept and iid in tile.reached
        else 0.0
        for tile in sound
    ]


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

"""Every feature of the dataset read as one, under one strategy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from visualization.common import aggregate, spread, tiles
from visualization.common.aggregate import Aggregate
from visualization.common.spread import Spread
from visualization.dataset.loading import Searched


@dataclass(frozen=True, slots=True)
class DatasetStats:
    """What one strategy would make of every feature searched.

    Attributes:
        strategy: The strategy the features were searched under.
        features: How many features were searched.
        gridded: How many of them hold ground any instrument reached.
        held: Every tile of every feature, read as one.
        split: How many tiles a feature is cut into, feature by feature.
        sizes: How much ground a tile holds, over the tiles searched.
        offered: How many observations each instrument landed on a tile, over
            the tiles searched, counting a tile it never reached as nothing.
        shared: The share of a tile exactly so many instruments reach between
            them, over the tiles kept, by how many of them reach it. A cell
            counts once, so the shares do not overlap and add up to what the
            window reaches.
        iids: The instruments reported on, in the order they are drawn.
        classes: How many tiles of each feature class were kept, and how many
            were searched, by feature class. A strategy admits a tile and
            never a feature, so a class is counted in tiles too.
    """

    strategy: str
    features: int
    gridded: int
    held: Aggregate
    split: Spread
    sizes: Spread
    offered: dict[str, Spread]
    shared: dict[int, Spread]
    iids: list[str]
    classes: dict[str, tuple[int, int]]


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
    reaching = [tiles.shared(tile.overlaps) for tile in grounded]
    return DatasetStats(
        strategy=strategy,
        features=len(held),
        gridded=sum(1 for searched in held if searched.tiles),
        held=aggregate.over(measured, iids),
        split=spread.over([searched.tiles for searched in held if searched.tiles]),
        sizes=spread.over([tile.area_km2 for tile in measured]),
        offered={
            iid: spread.over([tile.offered.get(iid, 0) for tile in measured])
            for iid in iids
        },
        shared={
            counted: spread.over(
                [
                    found.get(counted, 0.0) / tile.area_km2
                    for tile, found in zip(grounded, reaching, strict=True)
                ]
            )
            for counted in range(1, len(iids) + 1)
        },
        iids=iids,
        classes=_classes(held),
    )


def _classes(held: Sequence[Searched]) -> dict[str, tuple[int, int]]:
    """Count the tiles of each feature class the strategy keeps.

    Args:
        held: Every feature searched.

    Returns:
        The tiles kept and the tiles searched, by feature class, most searched
        first.
    """
    searched: dict[str, int] = {}
    passed: dict[str, int] = {}
    for one in held:
        searched[one.feature_class] = searched.get(one.feature_class, 0) + len(
            one.measured
        )
        passed[one.feature_class] = passed.get(one.feature_class, 0) + sum(
            1 for tile in one.measured if tile.kept
        )
    return {
        name: (passed.get(name, 0), counted)
        for name, counted in sorted(searched.items(), key=lambda one: -one[1])
    }

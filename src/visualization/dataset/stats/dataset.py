"""Every feature of the dataset read as one, under one strategy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from visualization.common import aggregate, spread
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
    return DatasetStats(
        strategy=strategy,
        features=len(held),
        gridded=sum(1 for searched in held if searched.tiles),
        held=aggregate.over(
            [tile for searched in held for tile in searched.measured], iids
        ),
        split=spread.over([searched.tiles for searched in held if searched.tiles]),
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

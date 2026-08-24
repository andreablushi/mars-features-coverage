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
        kept: How many of them left a tile in the dataset.
        held: Every tile of every feature, read as one.
        split: How many tiles a feature is cut into, feature by feature.
        kept_split: How many of them it keeps, over the features that keep
            any.
        iids: The instruments reported on, in the order they are drawn.
        classes: How many features of each class were kept, and how many were
            searched, by feature class.
    """

    strategy: str
    features: int
    gridded: int
    kept: int
    held: Aggregate
    split: Spread
    kept_split: Spread
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
    kept = [
        searched for searched in held if any(tile.kept for tile in searched.measured)
    ]
    iids = list(dict.fromkeys(iid for searched in held for iid in searched.iids))
    return DatasetStats(
        strategy=strategy,
        features=len(held),
        gridded=sum(1 for searched in held if searched.tiles),
        kept=len(kept),
        held=aggregate.over(
            [tile for searched in held for tile in searched.measured], iids
        ),
        split=spread.over([searched.tiles for searched in held if searched.tiles]),
        kept_split=spread.over(
            [sum(1 for tile in searched.measured if tile.kept) for searched in kept]
        ),
        iids=iids,
        classes=_classes(held, kept),
    )


def _classes(
    held: Sequence[Searched], kept: Sequence[Searched]
) -> dict[str, tuple[int, int]]:
    """Count the features of each class the strategy keeps.

    Args:
        held: Every feature searched.
        kept: Those of them that left a tile in the dataset.

    Returns:
        The features kept and the features searched, by feature class, most
        searched first.
    """
    searched: dict[str, int] = {}
    passed: dict[str, int] = {}
    for one in held:
        searched[one.feature_class] = searched.get(one.feature_class, 0) + 1
    for one in kept:
        passed[one.feature_class] = passed.get(one.feature_class, 0) + 1
    return {
        name: (passed.get(name, 0), counted)
        for name, counted in sorted(searched.items(), key=lambda one: -one[1])
    }

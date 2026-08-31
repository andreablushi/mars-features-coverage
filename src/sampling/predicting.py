"""Every feature of the dataset read as one, under one strategy."""

from __future__ import annotations

import math
from collections.abc import Sequence

from sampling import aggregating, configs, measuring
from sampling.models.dataset import ClassStats, DatasetStats, SearchedFeature
from sampling.models.spread import Spread
from sampling.models.tiles import TileStats


def predictions(searched: Sequence[SearchedFeature]) -> dict[str, DatasetStats]:
    """Read every strategy off one sweep of the features.

    Args:
        searched: What the sweep left, one entry per feature and strategy.

    Returns:
        What each strategy would make of them, by name, in the order swept.
    """
    by_strategy: dict[str, list[SearchedFeature]] = {}
    for feature in searched:
        by_strategy.setdefault(feature.strategy, []).append(feature)
    predicted: dict[str, DatasetStats] = {}
    for strategy, features in by_strategy.items():
        iids = list(dict.fromkeys(iid for one in features for iid in one.iids))
        tiles = [tile for one in features for tile in one.tiles if _plausible(tile)]
        grounded = [tile for tile in tiles if tile.kept and tile.area_km2]
        predicted[strategy] = DatasetStats(
            strategy=strategy,
            features=len(features),
            classes=_per_class(features, iids),
            tiles=aggregating.aggregate_tiles(tiles, iids),
            widths=Spread.over([math.sqrt(tile.area_km2) for tile in tiles]),
            offered={
                iid: Spread.over([tile.offered.get(iid, 0) for tile in tiles])
                for iid in iids
            },
            # The share of a tile every instrument at once reaches, tile by tile
            overlap=Spread.over(
                [
                    measuring.ground_by_instrument_count(tile.overlaps).get(
                        len(iids), 0.0
                    )
                    / tile.area_km2
                    for tile in grounded
                ]
            ),
            iids=iids,
        )
    return predicted


def _per_class(
    features: Sequence[SearchedFeature], iids: Sequence[str]
) -> dict[str, ClassStats]:
    """Read what a strategy made of the features of each class.

    Only the features it selected are counted, since a feature it refused
    outright would otherwise drag the class down to nothing.

    Args:
        features: What the sweep left of every feature searched under it.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What it made of each class, by feature class, in the order swept.
    """
    taken: dict[str, dict[str, list[float]]] = {}
    selected: dict[str, int] = {}
    for feature in features:
        kept = [
            tile
            for tile in feature.tiles
            if _plausible(tile) and tile.area_km2 and tile.kept
        ]
        if not kept:
            continue
        feature_class = feature.feature_class
        counts = taken.setdefault(feature_class, {iid: [] for iid in iids})
        selected[feature_class] = selected.get(feature_class, 0) + 1
        for iid in iids:
            counts[iid].append(
                sum(
                    tile.reached[iid].observations_taken
                    for tile in kept
                    if iid in tile.reached
                )
            )
    return {
        feature_class: ClassStats(
            selected=selected[feature_class],
            taken={iid: Spread.over(held) for iid, held in counts.items()},
        )
        for feature_class, counts in taken.items()
    }


def _plausible(tile: TileStats) -> bool:
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
    return max(shares) <= configs.SHARE_CEILING

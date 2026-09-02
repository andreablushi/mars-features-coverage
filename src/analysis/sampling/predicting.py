"""Every feature of the dataset read as one, under the filter."""

from __future__ import annotations

import math
from collections.abc import Sequence

from analysis.sampling import aggregating, measuring
from analysis.sampling.models.dataset import ClassStats, DatasetStats, SearchedFeature
from analysis.sampling.models.feature import FeatureStats
from analysis.sampling.models.spread import Spread


def prediction(searched: Sequence[SearchedFeature]) -> DatasetStats:
    """Read the dataset off one sweep of the features.

    Args:
        searched: What the sweep left, one entry per feature.

    Returns:
        What the filter would make of them.
    """
    iids = list(dict.fromkeys(iid for one in searched for iid in one.iids))
    measured = _measured(searched)
    grounded = [one for one in measured if one.kept and one.area_km2]
    return DatasetStats(
        features=len(searched),
        classes=_per_class(searched, iids),
        held=aggregating.aggregate_features(measured, iids),
        widths=Spread.over([math.sqrt(one.area_km2) for one in measured]),
        offered={
            iid: Spread.over([one.offered.get(iid, 0) for one in measured])
            for iid in iids
        },
        # The share of a feature every instrument at once reaches, one by one
        overlap=Spread.over(
            [
                measuring.ground_by_instrument_count(one.overlaps).get(len(iids), 0.0)
                / one.area_km2
                for one in grounded
            ]
        ),
        iids=iids,
    )


def _measured(features: Sequence[SearchedFeature]) -> list[FeatureStats]:
    """Keep every feature the search really left something readable on.

    Args:
        features: What the sweep left of every feature searched.

    Returns:
        What the search left on each of them, in the order they were swept.
    """
    return [
        one.stats
        for one in features
        if one.stats is not None and aggregating.plausible(one.stats)
    ]


def _per_class(
    features: Sequence[SearchedFeature], iids: Sequence[str]
) -> dict[str, ClassStats]:
    """Read what the filter made of the features of each class.

    Only the features it selected are counted, since a feature it refused
    outright would otherwise drag the class down to nothing.

    Args:
        features: What the sweep left of every feature searched.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What it made of each class, by feature class, in the order swept.
    """
    taken: dict[str, dict[str, list[float]]] = {}
    selected: dict[str, int] = {}
    for feature in features:
        stats = feature.stats
        if stats is None or not aggregating.plausible(stats):
            continue
        if not stats.area_km2 or not stats.kept:
            continue
        feature_class = feature.feature_class
        counts = taken.setdefault(feature_class, {iid: [] for iid in iids})
        selected[feature_class] = selected.get(feature_class, 0) + 1
        for iid in iids:
            reach = stats.reached.get(iid)
            counts[iid].append(reach.observations_taken if reach else 0)
    return {
        feature_class: ClassStats(
            selected=selected[feature_class],
            taken={iid: Spread.over(held) for iid, held in counts.items()},
        )
        for feature_class, counts in taken.items()
    }

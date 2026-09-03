"""Every feature of the dataset read as one, under the filter."""

from __future__ import annotations

import math
from collections.abc import Sequence

from analysis.sampling import aggregating, measuring
from analysis.sampling.models.dataset import ClassStats, DatasetStats, SearchedFeature
from analysis.sampling.models.spread import Spread


def prediction(searched: Sequence[SearchedFeature]) -> DatasetStats:
    """Read the dataset off one sweep of the features.

    Args:
        searched: What the sweep left, one entry per feature.

    Returns:
        What the filter would make of them.
    """
    iids = list(dict.fromkeys(iid for one in searched for iid in one.iids))
    # Read once here, since a feature claiming more ground than it holds is no
    # more readable per class than it is in all
    kept = [
        one
        for one in searched
        if one.stats is not None and aggregating.plausible(one.stats)
    ]
    measured = [one.stats for one in kept]
    grounded = [one for one in measured if one.kept]
    return DatasetStats(
        features=len(searched),
        classes=_per_class(kept, iids),
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


def _per_class(
    features: Sequence[SearchedFeature], iids: Sequence[str]
) -> dict[str, ClassStats]:
    """Read what the filter made of the features of each class.

    Only the features it selected are counted, since a feature it refused
    outright would otherwise drag the class down to nothing.

    Args:
        features: The features the sweep left something readable on.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What it made of each class, by feature class, in the order swept.
    """
    taken: dict[str, dict[str, list[float]]] = {}
    selected: dict[str, int] = {}
    for feature in features:
        stats = feature.stats
        if stats is None or not stats.kept:
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

"""Reading a run of features as one dataset, under the one filter."""

from __future__ import annotations

import math
from collections.abc import Sequence

from analysis.stats import configs
from analysis.stats.feature import measure
from analysis.stats.models.dataset import Aggregate, ClassStats, DatasetStats
from analysis.stats.models.feature import FeatureStats
from analysis.stats.models.spread import Spread


def dataset_stats(measured: Sequence[FeatureStats], searched: int) -> DatasetStats:
    """Read every feature the selection searched as one dataset.

    Args:
        measured: What the looks each feature keeps left on it, in any order.
        searched: How many features the selection searched, the ones holding
            nothing to measure counted in.

    Returns:
        What the filter left of them.
    """
    iids = list(dict.fromkeys(iid for one in measured for iid in one.iids))
    # Read once here, since a feature claiming more ground than it holds is no
    # more readable per class than it is in all
    held = [one for one in measured if plausible(one)]
    grounded = [one for one in held if one.window.kept]
    return DatasetStats(
        features=searched,
        classes=_stats_per_class(held, iids),
        held=aggregate_features(held, iids),
        widths=Spread.over([math.sqrt(one.window.area_km2) for one in held]),
        offered={
            iid: Spread.over([one.offered.get(iid, 0) for one in held]) for iid in iids
        },
        # The share of a feature every instrument at once reaches, one by one
        overlap=Spread.over(
            [
                measure.ground_by_instrument_count(one.overlaps).get(len(iids), 0.0)
                / one.window.area_km2
                for one in grounded
            ]
        ),
        iids=iids,
    )


def aggregate_features(
    measured: Sequence[FeatureStats], iids: Sequence[str]
) -> Aggregate:
    """Read a run of features as one.

    Args:
        measured: The features something readable was left on, in any order.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What they hold between them.
    """
    kept = [one for one in measured if one.window.kept]
    # Two features may share ground, so their overlaps are added as an upper bound
    overlaps: dict[tuple[str, ...], float] = {}
    for feature in kept:
        for instrument_names, km2 in feature.overlaps.items():
            overlaps[instrument_names] = overlaps.get(instrument_names, 0.0) + km2
    return Aggregate(
        searched=len(measured),
        kept=len(kept),
        area_km2=sum(one.window.area_km2 for one in measured),
        days=Spread.over([one.window.days for one in kept]),
        geo_mean=Spread.over([one.window.geo_mean for one in kept]),
        reached={
            iid: Spread.over(
                [
                    feature.reached[iid].km2 / feature.window.area_km2
                    if iid in feature.reached
                    else 0.0
                    for feature in kept
                ]
            )
            for iid in iids
        },
        landed={iid: _pixels_landed(kept, iid) for iid in iids},
        pixels_per_look={iid: _pixels_per_look(kept, iid) for iid in iids},
        # A pixel is the same size wherever it falls, so every searched feature says
        pixel_km2={
            iid: Spread.over(
                [one.pixel_km2[iid] for one in measured if iid in one.pixel_km2]
            )
            for iid in iids
        },
        overlaps=dict(sorted(overlaps.items(), key=lambda ground: -ground[1])),
    )


def plausible(feature: FeatureStats) -> bool:
    """Say whether a feature reports no more ground than it holds.

    Args:
        feature: One feature the search ran over.

    Returns:
        Whether every share it reports sits inside the ceiling.
    """
    area_km2 = feature.window.area_km2
    shares = [reach.km2 / area_km2 for reach in feature.reached.values()]
    shares.append(sum(feature.overlaps.values()) / area_km2)
    shares.append(feature.window.geo_mean)
    return max(shares) <= configs.SHARE_CEILING


def _stats_per_class(
    measured: Sequence[FeatureStats], iids: Sequence[str]
) -> dict[str, ClassStats]:
    """Read what the filter left of the features of each class, the selected only.

    Args:
        measured: The features something readable was left on.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What it left of each class, by feature class, in the order read.
    """
    taken: dict[str, dict[str, list[float]]] = {}
    selected: dict[str, int] = {}
    for feature in measured:
        if not feature.window.kept:
            continue
        feature_class = feature.window.feature_class
        counts = taken.setdefault(feature_class, {iid: [] for iid in iids})
        selected[feature_class] = selected.get(feature_class, 0) + 1
        for iid in iids:
            reach = feature.reached.get(iid)
            counts[iid].append(reach.observations_taken if reach else 0)
    return {
        feature_class: ClassStats(
            selected=selected[feature_class],
            taken={iid: Spread.over(held) for iid, held in counts.items()},
        )
        for feature_class, counts in taken.items()
    }


def _pixels_landed(kept: Sequence[FeatureStats], iid: str) -> Spread:
    """Read how many pixels one instrument lands on a feature, feature by feature.

    Args:
        kept: The features that earned a window.
        iid: The instrument to read.

    Returns:
        The pixels it lands on a feature, leaving out one carrying no count.
    """
    landed: list[float] = []
    for feature in kept:
        reach = feature.reached.get(iid)
        if reach is None:
            landed.append(0.0)
        elif reach.pixels is not None:
            landed.append(reach.pixels)
    return Spread.over(landed)


def _pixels_per_look(kept: Sequence[FeatureStats], iid: str) -> Spread:
    """Read how many pixels one observation of an instrument lands on a feature.

    Args:
        kept: The features that earned a window.
        iid: The instrument to read.

    Returns:
        The pixels one of its observations landed, feature by feature, leaving
        out a feature carrying no pixel count.
    """
    per_look: list[float] = []
    for feature in kept:
        reach = feature.reached.get(iid)
        if reach is None or not reach.observations_taken or reach.pixels is None:
            continue
        per_look.append(reach.pixels / reach.observations_taken)
    return Spread.over(per_look)

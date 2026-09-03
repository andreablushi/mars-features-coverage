"""Reading a run of features as one, whatever dataset they belong to."""

from __future__ import annotations

from collections.abc import Sequence

from analysis.sampling import configs
from analysis.sampling.models.feature import Aggregate, FeatureStats
from analysis.sampling.models.spread import Spread


def aggregate_features(
    searched: Sequence[FeatureStats], iids: Sequence[str]
) -> Aggregate:
    """Read a run of features as one.

    Args:
        searched: The features the search left something readable on, in any order.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What they hold between them.
    """
    kept = [feature for feature in searched if feature.kept]
    # Two features may share ground, so their overlaps are added as an upper bound
    overlaps: dict[tuple[str, ...], float] = {}
    for feature in kept:
        for instrument_names, km2 in feature.overlaps.items():
            overlaps[instrument_names] = overlaps.get(instrument_names, 0.0) + km2
    return Aggregate(
        searched=len(searched),
        kept=len(kept),
        area_km2=sum(feature.area_km2 for feature in searched),
        kept_km2=sum(feature.area_km2 for feature in kept),
        days=Spread.over([feature.days for feature in kept]),
        geo_mean=Spread.over([feature.geo_mean for feature in kept]),
        reached={
            iid: Spread.over(
                [
                    feature.reached[iid].km2 / feature.area_km2
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
                [
                    feature.pixel_km2[iid]
                    for feature in searched
                    if iid in feature.pixel_km2
                ]
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
    shares = [reach.km2 / feature.area_km2 for reach in feature.reached.values()]
    shares.append(sum(feature.overlaps.values()) / feature.area_km2)
    shares.append(feature.geo_mean)
    return max(shares) <= configs.SHARE_CEILING


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

    A feature the instrument took nothing on says nothing about what one of its
    looks is worth, so it is left out rather than counted as nought.

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

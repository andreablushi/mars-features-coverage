"""Accumulating one instrument set's coverage of one feature through time.

The set's observations are walked once in chronological order and folded into a
running union. What each adds is the growth of that union, so a single pass
yields both the spike at an observation's own timestamp and the cumulative
curve behind it, without binning anything. Binning stays a choice made when
plotting.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.computation.region import FeatureRegion
from analysis.computation.tiles import TiledUnion
from analysis.models.feature import FeatureBox
from analysis.models.projected import ProjectedObservation
from analysis.models.results import Event, Summary


def compute(
    box: FeatureBox,
    region: FeatureRegion,
    observations: Sequence[ProjectedObservation],
) -> tuple[list[Event], Summary, BaseGeometry]:
    """Measure how one instrument set covers one feature over time.

    Args:
        box: The feature the coverage is measured against.
        region: That feature projected into equal-area metres.
        observations: The set's observations in chronological order.

    Returns:
        One event row per observation, the summary row for the set, and the
        set's final union so the pooled row can be assembled from it later.
    """
    covered = TiledUnion(region)
    gridded = observations[0].set_key in configs.GRIDDED_SETS
    events = [
        _event(
            box, observation, covered, covered.add(observation.shape), region, gridded
        )
        for observation in observations
    ]
    summary = summarise(
        box.feature_class,
        box.name,
        observations[0].set_key,
        region.area_m2,
        covered.area_m2,
        len(events),
        sum(event.contributed for event in events),
        events[0].t_start,
        events[-1].t_start,
        gridded,
    )
    return events, summary, covered.shape


def _event(
    box: FeatureBox,
    observation: ProjectedObservation,
    covered: TiledUnion,
    fresh_m2: float,
    region: FeatureRegion,
    gridded: bool,
) -> Event:
    """Record what one observation contributed.

    Args:
        box: The feature being covered.
        observation: The observation being recorded.
        covered: The running union, already including this observation.
        fresh_m2: The ground this observation added to it.
        region: The projected feature, for the share of it covered.
        gridded: Whether the set is a whole-planet basemap.

    Returns:
        The event row.
    """
    return Event(
        feature_class=box.feature_class,
        feature_name=box.name,
        ihid=observation.ihid,
        iid=observation.iid,
        pt=observation.pt,
        pdsid=observation.pdsid,
        t_start=observation.start,
        t_stop=observation.stop,
        own_km2=observation.shape.area / 1e6,
        new_km2=fresh_m2 / 1e6,
        cum_km2=covered.area_m2 / 1e6,
        cum_frac=covered.area_m2 / region.area_m2,
        contributed=fresh_m2 > 0.0,
        width_km=observation.width_km,
        width_source=observation.width_source,
        gridded=gridded,
    )


def summarise(
    feature_class: str,
    feature_name: str,
    key: tuple[str, str, str],
    total_m2: float,
    covered_m2: float,
    count: int,
    contributing: int | None,
    first: datetime | None,
    last: datetime | None,
    gridded: bool,
) -> Summary:
    """Build one summary row.

    Args:
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.
        key: The instrument host, instrument, and product type.
        total_m2: The area of the whole feature.
        covered_m2: The ground the row's observations reached.
        count: How many observations the row covers.
        contributing: How many added ground nothing had covered, or None.
        first: When the earliest of them started.
        last: When the latest of them started.
        gridded: Whether the row describes a whole-planet basemap.

    Returns:
        The summary row.
    """
    area_km2 = total_m2 / 1e6
    covered_frac = covered_m2 / total_m2
    return Summary(
        feature_class=feature_class,
        feature_name=feature_name,
        ihid=key[0],
        iid=key[1],
        pt=key[2],
        feature_area_km2=area_km2,
        covered_km2=covered_frac * area_km2,
        covered_frac=covered_frac,
        n_obs=count,
        n_contributing=contributing,
        t_first=first,
        t_last=last,
        span_days=(last - first).total_seconds() / 86400.0 if first and last else None,
        gridded=gridded,
    )

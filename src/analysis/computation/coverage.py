"""Accumulating one instrument set's coverage of one feature through time.

The set's observations are walked once in chronological order and folded into a
running union. What each adds is the growth of that union, so a single pass
yields both the spike at an observation's own timestamp and the cumulative
curve behind it, without binning anything. Binning stays a choice made when
plotting.
"""

from __future__ import annotations

from collections.abc import Sequence

from analysis.computation.region import FeatureRegion
from analysis.computation.tiles import TiledUnion
from analysis.models.feature import FeatureBox
from analysis.models.projected import ProjectedObservation
from analysis.models.results import Event, Summary


def compute(
    box: FeatureBox,
    region: FeatureRegion,
    observations: Sequence[ProjectedObservation],
) -> tuple[list[Event], Summary]:
    """Measure how one instrument set covers one feature over time.

    Args:
        box: The feature the coverage is measured against.
        region: That feature projected into equal-area metres.
        observations: The set's observations in chronological order.

    Returns:
        One event row per observation and the summary row for the set.
    """
    covered = TiledUnion(region)
    events = [
        _event(box, observation, covered, covered.add(observation.shape), region)
        for observation in observations
    ]
    return events, _summary(box, observations[0].set_key, region, covered, events)


def _event(
    box: FeatureBox,
    observation: ProjectedObservation,
    covered: TiledUnion,
    fresh_m2: float,
    region: FeatureRegion,
) -> Event:
    """Record what one observation contributed.

    Args:
        box: The feature being covered.
        observation: The observation being recorded.
        covered: The running union, already including this observation.
        fresh_m2: The ground this observation added to it.
        region: The projected feature, for the share of it covered.

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
        width_km=observation.width_km,
        width_source=observation.width_source,
    )


def _summary(
    box: FeatureBox,
    key: tuple[str, str, str],
    region: FeatureRegion,
    covered: TiledUnion,
    events: Sequence[Event],
) -> Summary:
    """Build the one row describing a finished instrument set.

    Args:
        box: The feature the coverage was measured against.
        key: The instrument host, instrument, and product type.
        region: That feature projected into equal-area metres.
        covered: The union of everything the set reached.
        events: The set's event rows, in chronological order.

    Returns:
        The summary row.
    """
    area_km2 = region.area_m2 / 1e6
    first, last = events[0].t_start, events[-1].t_start
    return Summary(
        feature_class=box.feature_class,
        feature_name=box.name,
        ihid=key[0],
        iid=key[1],
        pt=key[2],
        feature_area_km2=area_km2,
        covered_km2=covered.area_m2 / 1e6,
        covered_frac=covered.area_m2 / region.area_m2,
        n_obs=len(events),
        t_first=first,
        t_last=last,
        span_days=(last - first).total_seconds() / 86400.0,
    )

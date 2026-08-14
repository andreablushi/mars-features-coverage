"""Accumulating one instrument set's coverage of one feature through time.

The set's observations are walked once in chronological order and folded into a
running union. What each adds is the growth of that union, so a single pass
yields both the spike at an observation's own timestamp and the cumulative
curve behind it, without binning anything. Binning stays a choice made when
plotting.

The union is also the expensive half of the work, since every insert is real
vector geometry, so it can be left out. What survives without it is each
observation's own footprint area and the set's shape in time; what is lost is
anything cumulative, and those columns are written empty rather than zero so a
run that skipped the union cannot be mistaken for one that found no overlap.
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
    *,
    cumulative_union: bool = True,
) -> tuple[list[Event], Summary]:
    """Measure how one instrument set covers one feature over time.

    Args:
        box: The feature the coverage is measured against.
        region: That feature projected into equal-area metres.
        observations: The set's observations in chronological order.
        cumulative_union: Whether to accumulate the running union. When False
            every cumulative column is left empty.

    Returns:
        One event row per observation and the summary row for the set.
    """
    covered = TiledUnion(region) if cumulative_union else None
    events = [
        _event(box, observation, covered, _add(covered, observation), region)
        for observation in observations
    ]
    return events, _summary(box, observations[0].set_key, region, covered, events)


def _add(covered: TiledUnion | None, observation: ProjectedObservation) -> float | None:
    """Fold one footprint into the union, when there is a union to fold into.

    Args:
        covered: The running union, or None when it is not being kept.
        observation: The observation being added.

    Returns:
        The ground it added, or None when no union is being kept.
    """
    return None if covered is None else covered.add(observation.shape)


def _event(
    box: FeatureBox,
    observation: ProjectedObservation,
    covered: TiledUnion | None,
    fresh_m2: float | None,
    region: FeatureRegion,
) -> Event:
    """Record what one observation contributed.

    Args:
        box: The feature being covered.
        observation: The observation being recorded.
        covered: The running union already including this observation, or None
            when no union is being kept.
        fresh_m2: The ground this observation added to it, or None.
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
        new_km2=None if fresh_m2 is None else fresh_m2 / 1e6,
        cum_km2=None if covered is None else covered.area_m2 / 1e6,
        cum_frac=None if covered is None else covered.area_m2 / region.area_m2,
        width_km=observation.width_km,
        width_source=observation.width_source,
    )


def _summary(
    box: FeatureBox,
    key: tuple[str, str, str],
    region: FeatureRegion,
    covered: TiledUnion | None,
    events: Sequence[Event],
) -> Summary:
    """Build the one row describing a finished instrument set.

    Args:
        box: The feature the coverage was measured against.
        key: The instrument host, instrument, and product type.
        region: That feature projected into equal-area metres.
        covered: The union of everything the set reached, or None when no union
            was kept.
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
        covered_km2=None if covered is None else covered.area_m2 / 1e6,
        covered_frac=None if covered is None else covered.area_m2 / region.area_m2,
        n_obs=len(events),
        t_first=first,
        t_last=last,
        span_days=(last - first).total_seconds() / 86400.0,
    )

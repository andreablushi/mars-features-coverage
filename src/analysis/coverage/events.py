"""Accumulating one instrument set's coverage of one feature through time."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from analysis.coverage import union
from analysis.geometry.region import FeatureRegion
from models.feature import Feature
from models.observation import LoadedSet, ProjectedObservation
from models.results import Event, Summary


def measure_set(
    loaded: LoadedSet[ProjectedObservation],
    region: FeatureRegion,
    *,
    cumulative_union: bool = True,
) -> tuple[list[Event], Summary]:
    """Measure how one instrument set covers one feature over time.

    Args:
        loaded: The set's projected observations in chronological order, with
            the feature and the set identifier they belong to.
        region: That feature projected into equal-area metres.
        cumulative_union: Whether to accumulate the running union. When False
            every cumulative column is left empty.

    Returns:
        One event row per observation and the summary row for the set.
    """
    feature, observations = loaded.feature, loaded.observations
    fresh, cumulative = _running_totals(region, observations, cumulative_union)
    events = [
        _observation_row(feature, observation, region, fresh, cumulative, position)
        for position, observation in enumerate(observations)
    ]
    return events, _set_summary_row(
        feature, loaded.set_key, observations[0].set_key, region, cumulative, events
    )


def _running_totals(
    region: FeatureRegion,
    observations: Sequence[ProjectedObservation],
    cumulative_union: bool,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Run the union over the set, when there is a union to run.

    Args:
        region: The projected feature the footprints are cut to.
        observations: The set's observations in chronological order.
        cumulative_union: Whether to accumulate the running union.

    Returns:
        The new ground each observation covered and the running total behind
        it, both in square metres, or a pair of Nones when no union was kept.
    """
    if not cumulative_union:
        return None, None
    fresh = union.new_ground(
        region, [observation.shape for observation in observations]
    )
    return fresh, np.cumsum(fresh)


def _observation_row(
    feature: Feature,
    observation: ProjectedObservation,
    region: FeatureRegion,
    fresh: np.ndarray | None,
    cumulative: np.ndarray | None,
    position: int,
) -> Event:
    """Record what one observation contributed.

    Args:
        feature: The feature being covered.
        observation: The observation being recorded.
        region: The projected feature, for the share of it covered.
        fresh: The new ground every observation covered, or None when no union
            was kept.
        cumulative: The running total behind every observation, or None.
        position: Where this observation sits in those arrays.

    Returns:
        The event row.
    """
    return Event(
        feature_class=feature.feature_class,
        feature_name=feature.name,
        ihid=observation.ihid,
        iid=observation.iid,
        pt=observation.pt,
        pdsid=observation.pdsid,
        t_start=observation.start,
        t_stop=observation.stop,
        own_km2=observation.shape.area / 1e6,
        new_km2=None if fresh is None else float(fresh[position]) / 1e6,
        cum_km2=None if cumulative is None else float(cumulative[position]) / 1e6,
        cum_frac=(
            None if cumulative is None else float(cumulative[position]) / region.area_m2
        ),
        width_km=observation.width_km,
        width_source=observation.width_source,
    )


def _set_summary_row(
    feature: Feature,
    set_key: str,
    key: tuple[str, str, str],
    region: FeatureRegion,
    cumulative: np.ndarray | None,
    events: Sequence[Event],
) -> Summary:
    """Build the one row describing a finished instrument set.

    Args:
        feature: The feature the coverage was measured against.
        set_key: The instrument set identifier the records were asked for by.
        key: The instrument host, instrument, and product type.
        region: That feature projected into equal-area metres.
        cumulative: The running total behind every observation, or None when no
            union was kept.
        events: The set's event rows, in chronological order.

    Returns:
        The summary row.
    """
    area_km2 = region.area_m2 / 1e6
    covered_m2 = None if cumulative is None else float(cumulative[-1])
    first, last = events[0].t_start, events[-1].t_start
    return Summary(
        feature_class=feature.feature_class,
        feature_name=feature.name,
        set_key=set_key,
        ihid=key[0],
        iid=key[1],
        pt=key[2],
        feature_area_km2=area_km2,
        covered_km2=None if covered_m2 is None else covered_m2 / 1e6,
        covered_frac=None if covered_m2 is None else covered_m2 / region.area_m2,
        n_obs=len(events),
        t_first=first,
        t_last=last,
        span_days=(last - first).total_seconds() / 86400.0,
    )

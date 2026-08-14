"""Accumulating one instrument set's coverage of one feature through time.

The set's observations are laid over a tile grid and accumulated in
chronological order, so each is measured against everything before it. A single
pass yields both the spike at an observation's own timestamp and the cumulative
curve behind it, without binning anything. Binning stays a plotting choice.

The union is also the expensive half of the work, since every insert is real
vector geometry, so it can be left out. What survives without it is each
observation's own footprint area and the set's shape in time; what is lost is
anything cumulative, and those columns are written empty rather than zero so a
run that skipped the union cannot be mistaken for one that found no overlap.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from analysis.computation import union
from analysis.computation.region import FeatureRegion
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
    fresh, cumulative = _accumulate(region, observations, cumulative_union)
    events = [
        _event(box, observation, region, fresh, cumulative, position)
        for position, observation in enumerate(observations)
    ]
    return events, _summary(box, observations[0].set_key, region, cumulative, events)


def _accumulate(
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
    fresh = union.accumulate(
        region, [observation.shape for observation in observations]
    )
    return fresh, np.cumsum(fresh)


def _event(
    box: FeatureBox,
    observation: ProjectedObservation,
    region: FeatureRegion,
    fresh: np.ndarray | None,
    cumulative: np.ndarray | None,
    position: int,
) -> Event:
    """Record what one observation contributed.

    Args:
        box: The feature being covered.
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
        feature_class=box.feature_class,
        feature_name=box.name,
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


def _summary(
    box: FeatureBox,
    key: tuple[str, str, str],
    region: FeatureRegion,
    cumulative: np.ndarray | None,
    events: Sequence[Event],
) -> Summary:
    """Build the one row describing a finished instrument set.

    Args:
        box: The feature the coverage was measured against.
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
        feature_class=box.feature_class,
        feature_name=box.name,
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

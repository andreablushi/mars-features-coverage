"""Accumulating one instrument set's coverage of one feature through time."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from analysis.coverage import union
from analysis.coverage.raster import FeatureRaster
from analysis.geometry.region import FeatureRegion
from analysis.models.observation import LoadedSet, ProjectedObservation
from models.feature import Feature
from models.results import Event, Summary


def measure_set(
    loaded: LoadedSet[ProjectedObservation],
    region: FeatureRegion,
) -> tuple[list[Event], Summary]:
    """Measure how one instrument set covers one feature over time.

    Args:
        loaded: The set's projected observations in chronological order, with
            the feature and the set identifier they belong to.
        region: That feature projected into equal-area metres.

    Returns:
        One observation row per observation and the summary row for the set.

    Note:
        The union runs sector by sector so each insert touches a small shape
        and the sectors run in parallel; the cost is rounding where a footprint
        crosses a seam, which leaves the ground it is credited with within a
        part in 10^10 of the ground it actually covers.
    """
    feature, observations = loaded.feature, loaded.observations
    fresh = union.new_ground(region, [o.shape for o in observations])
    cumulative = np.cumsum(fresh)
    grid = FeatureRaster(region)
    observations = [
        _observation_row(
            feature, observation, region, fresh, cumulative, position, grid
        )
        for position, observation in enumerate(observations)
    ]
    return observations, _set_summary_row(
        feature,
        loaded.set_key,
        observations[0],
        region,
        cumulative,
        observations,
        grid,
    )


def _observation_row(
    feature: Feature,
    observation: ProjectedObservation,
    region: FeatureRegion,
    fresh: np.ndarray,
    cumulative: np.ndarray,
    position: int,
    grid: FeatureRaster,
) -> Event:
    """Record what one observation contributed.

    Args:
        feature: The feature being covered.
        observation: The observation being recorded.
        region: The projected feature, for the share of it covered.
        fresh: The new ground every observation covered.
        cumulative: The running total behind every observation.
        position: Where this observation sits in those arrays.
        grid: The feature's cells, which the footprint is burned into.

    Returns:
        The observation row.
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
        new_km2=float(fresh[position]) / 1e6,
        cum_km2=float(cumulative[position]) / 1e6,
        cum_frac=float(cumulative[position]) / region.area_m2,
        width_km=observation.width_km,
        pixels=observation.shape.area / 1e6 / observation.pixel_km2,
        mask=grid.burn(observation.shape),
    )


def _set_summary_row(
    feature: Feature,
    set_key: str,
    observation: ProjectedObservation,
    region: FeatureRegion,
    cumulative: np.ndarray,
    observations: Sequence[Event],
    grid: FeatureRaster,
) -> Summary:
    """Build the one row describing a finished instrument set.

    Args:
        feature: The feature the coverage was measured against.
        set_key: The instrument set identifier the records were asked for by.
        observation: Any of the set's observations, which all name the same
            instrument host, instrument, and product type.
        region: That feature projected into equal-area metres.
        cumulative: The running total behind every observation.
        observations: The set's observation rows, in chronological order.
        grid: The feature's cells, which the coverage was measured on.

    Returns:
        The summary row.
    """
    covered_m2 = float(cumulative[-1])
    first, last = observations[0].t_start, observations[-1].t_start
    return Summary(
        feature_class=feature.feature_class,
        feature_name=feature.name,
        set_key=set_key,
        ihid=observation.ihid,
        iid=observation.iid,
        pt=observation.pt,
        feature_area_km2=region.area_m2 / 1e6,
        covered_km2=covered_m2 / 1e6,
        covered_frac=covered_m2 / region.area_m2,
        n_obs=len(observations),
        t_first=first,
        t_last=last,
        span_days=(last - first).total_seconds() / 86400.0,
        mask_cells=grid.cells,
        pixels=sum(observation.pixels for observation in observations),
        grid_side=grid.side,
        tiles_across=grid.across,
        cell_km2=grid.cell_km2,
        grid_mask=grid.mask,
    )

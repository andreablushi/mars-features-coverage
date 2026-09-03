"""Measuring how one instrument set covers one feature through time."""

from __future__ import annotations

import numpy as np

from analysis.coverage.accumulating import union
from analysis.coverage.accumulating.rasterizing import FeatureRaster
from analysis.coverage.models.coverage import Event
from analysis.coverage.models.observation import ProjectedSet
from analysis.coverage.models.summary import Summary


def measure_set(
    projected: ProjectedSet, grid_cells: int
) -> tuple[list[Event], Summary]:
    """Measure how one instrument set covers one feature over time.

    Args:
        projected: The set's ground on the feature, in chronological order.
        grid_cells: How many cells one block of the feature's grid holds per axis.

    Returns:
        One row per observation and the single row describing the set.
    """
    feature, region = projected.feature, projected.region
    observations = projected.observations
    fresh = union.new_ground(region, [one.shape for one in observations])
    cumulative = np.cumsum(fresh)
    raster = FeatureRaster(region, grid_cells)
    events = [
        Event(
            feature_class=feature.feature_class,
            feature_name=feature.name,
            ihid=observation.ihid,
            iid=observation.iid,
            pt=observation.pt,
            pdsid=observation.pdsid,
            t_start=observation.start,
            t_stop=observation.stop,
            own_km2=observation.shape.area / 1e6,
            new_km2=float(first_seen) / 1e6,
            cum_km2=float(covered) / 1e6,
            cum_frac=float(covered) / region.area_m2,
            width_km=observation.width_km,
            pixels=observation.shape.area / 1e6 / observation.pixel_km2,
            mask=raster.burn(observation.shape),
        )
        for observation, first_seen, covered in zip(
            observations, fresh, cumulative, strict=True
        )
    ]
    first, last = events[0].t_start, events[-1].t_start
    return events, Summary(
        feature_class=feature.feature_class,
        feature_name=feature.name,
        set_key=projected.set_key,
        ihid=events[0].ihid,
        iid=events[0].iid,
        pt=events[0].pt,
        feature_area_km2=region.area_m2 / 1e6,
        covered_km2=float(cumulative[-1]) / 1e6,
        covered_frac=float(cumulative[-1]) / region.area_m2,
        n_obs=len(events),
        t_first=first,
        t_last=last,
        span_days=(last - first).total_seconds() / 86400.0,
        mask_cells=raster.cells,
        pixels=sum(event.pixels for event in events),
        grid_side=raster.side,
        cell_km2=raster.cell_km2,
        grid_mask=raster.mask,
    )

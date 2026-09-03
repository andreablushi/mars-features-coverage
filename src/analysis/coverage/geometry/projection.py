"""Turning stored observations into projected ground on their feature."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from shapely import from_wkt

from analysis.coverage import records
from analysis.coverage.geometry import footprints
from analysis.coverage.geometry.region import FeatureRegion
from analysis.coverage.models.observation import (
    LoadedSet,
    Observation,
    ProjectedObservation,
)
from analysis.coverage.utils import geodesy, pixels, swath
from analysis.models.job import Job


def load_projected(
    job: Job,
) -> tuple[LoadedSet[ProjectedObservation], FeatureRegion]:
    """Project one set's stored footprints onto its feature.

    Args:
        job: The instrument set being computed.

    Returns:
        The projected set and the region it was measured against.
    """
    loaded = records.load_set(job.source)
    region = FeatureRegion(loaded.feature)
    projected, missed = project(region, loaded.observations, loaded.set_key)
    return (
        LoadedSet(
            feature=loaded.feature,
            set_key=loaded.set_key,
            observations=projected,
            discarded=loaded.discarded + missed,
        ),
        region,
    )


def project(
    region: FeatureRegion, observations: Sequence[Observation], set_key: str
) -> tuple[list[ProjectedObservation], int]:
    """Project every observation's footprint onto its feature.

    Args:
        region: The projected feature the footprints are cut to.
        observations: The observations to project.
        set_key: The instrument set the observations were asked for by.

    Returns:
        The observations that landed on the feature, and how many missed it entirely.
    """
    resolved = _track_widths(observations)
    shapes = region.footprint_areas(
        from_wkt(
            np.asarray([observation.wkt for observation in observations], dtype=object)
        ),
        np.asarray([width or 0.0 for width in resolved], dtype=float),
    )
    projected = []
    missed = 0
    for observation, width_m, shape in zip(observations, resolved, shapes, strict=True):
        if shape.is_empty:
            missed += 1
            continue
        width_km = width_m / 1000.0 if width_m is not None else None
        projected.append(
            ProjectedObservation(
                pdsid=observation.pdsid,
                ihid=observation.ihid,
                iid=observation.iid,
                pt=observation.pt,
                start=observation.start,
                stop=observation.stop,
                shape=shape,
                width_km=width_km,
                pixel_km2=pixels.ground_pixel_km2(
                    set_key, observation.map_scale_m, width_km
                ),
            )
        )
    return projected, missed


def _track_widths(observations: Sequence[Observation]) -> list[float | None]:
    """Derive a swath width for every ground track among the observations.

    Args:
        observations: The observations to inspect.

    Returns:
        One width in metres per observation, and None where the footprint has area.
    """
    widths: list[float | None] = [None] * len(observations)
    for position, observation in enumerate(observations):
        if not observation.is_track or observation.duration_s <= 0.0:
            continue
        # A track is published as lines, whose ground lengths add up to its own
        length = 0.0
        parts, _ = footprints.single_parts(
            np.asarray([from_wkt(observation.wkt)], dtype=object)
        )
        for part in parts:
            if part.geom_type == "LineString":
                coords = np.asarray(part.coords)
                length += geodesy.haversine_length(coords[:, 0], coords[:, 1])
        if length > 0.0:
            widths[position] = swath.track_width(length, observation.duration_s)
    return widths

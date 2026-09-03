"""Putting one instrument set's stored footprints onto the ground of its feature."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from shapely import from_wkt

from analysis.coverage.models.observation import ProjectedObservation, ProjectedSet
from analysis.coverage.projection.geometry import footprints, geodesy, sizing
from analysis.coverage.projection.region import FeatureRegion
from analysis.models.observation import Observation, ObservationSet


def project(loaded: ObservationSet) -> ProjectedSet:
    """Project one set's footprints onto its feature and cut them to it.

    Args:
        loaded: The set's stored observations, in chronological order.

    Returns:
        The observations that landed on the feature, and the region they were cut to.
    """
    region = FeatureRegion(loaded.feature)
    widths = _track_widths(loaded.observations)
    shapes = region.footprint_areas(
        from_wkt(
            np.asarray(
                [observation.wkt for observation in loaded.observations], dtype=object
            )
        ),
        np.asarray([width or 0.0 for width in widths], dtype=float),
    )
    projected = []
    missed = 0
    for observation, width_m, shape in zip(
        loaded.observations, widths, shapes, strict=True
    ):
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
                pixel_km2=sizing.ground_pixel_km2(
                    loaded.set_key, observation.map_scale_m, width_km
                ),
            )
        )
    return ProjectedSet(
        feature=loaded.feature,
        set_key=loaded.set_key,
        region=region,
        observations=projected,
        discarded=loaded.discarded + missed,
    )


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
            widths[position] = sizing.track_width(length, observation.duration_s)
    return widths

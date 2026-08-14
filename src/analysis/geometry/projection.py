"""Turning stored observations into projected ground on their feature."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from shapely import from_wkt

from analysis.geometry import footprints
from analysis.geometry.region import FeatureRegion
from analysis.utils import geodesy, swath
from models.observation import Observation, ProjectedObservation


def project(
    region: FeatureRegion, observations: Sequence[Observation]
) -> tuple[list[ProjectedObservation], int]:
    """Project every observation's footprint onto its feature.

    An observation whose footprint misses the feature entirely is dropped, since
    a zero reads as a measurement of no ground rather than the absence of one.

    Args:
        region: The projected feature the footprints are cut to.
        observations: The observations to project.

    Returns:
        The projected observations that landed on the feature, in the order
        they were given, and how many missed it entirely.
    """
    widths = _track_widths(observations)
    resolved = [
        widths.get(observation.pdsid, (0.0, None)) for observation in observations
    ]
    shapes = region.footprint_areas(
        from_wkt(
            np.asarray([observation.wkt for observation in observations], dtype=object)
        ),
        np.asarray([width for width, _ in resolved], dtype=float),
    )
    projected = []
    missed = 0
    for observation, (width_m, source), shape in zip(
        observations, resolved, shapes, strict=True
    ):
        if shape.is_empty:
            missed += 1
            continue
        projected.append(
            ProjectedObservation(
                pdsid=observation.pdsid,
                ihid=observation.ihid,
                iid=observation.iid,
                pt=observation.pt,
                start=observation.start,
                stop=observation.stop,
                shape=shape,
                width_km=width_m / 1000.0 if source else None,
                width_source=source,
            )
        )
    return projected, missed


def _track_widths(
    observations: Sequence[Observation],
) -> dict[str, tuple[float, str]]:
    """Derive a swath width for every ground track among the observations.

    Args:
        observations: The observations to inspect.

    Returns:
        The width in metres and its source, keyed by product identifier, for
        the track footprints only.
    """
    tracks = [observation for observation in observations if observation.is_track]
    if not tracks:
        return {}
    measurements = [
        (_track_length(observation.wkt), observation.duration_s)
        for observation in tracks
    ]
    resolved = swath.resolve_widths(measurements)
    return {
        observation.pdsid: width
        for observation, width in zip(tracks, resolved, strict=True)
    }


def _track_length(wkt: str) -> float:
    """Return the full ground length of a track footprint.

    The whole track is measured, not the part inside the feature, because the
    length is only used with the observation's duration to recover the ground
    speed the spacecraft flew at.

    Args:
        wkt: The footprint as well-known text.

    Returns:
        The summed length in metres.
    """
    total = 0.0
    for part in footprints.flatten(footprints.parse(wkt)):
        if part.geom_type != "LineString":
            continue
        coords = np.asarray(part.coords)
        total += geodesy.haversine_length(coords[:, 0], coords[:, 1])
    return total

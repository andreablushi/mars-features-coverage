"""Turning stored observations into projected ground on their feature.

This is the half of the computation that depends only on the footprint and the
feature it is measured against, never on the other observations. It produces
the same answer on every run, which is what makes it worth caching.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from analysis.computation import footprints, geodesy, swath
from analysis.computation.region import FeatureRegion
from analysis.models.observation import Observation
from analysis.models.projected import ProjectedObservation


def project(
    region: FeatureRegion, observations: Sequence[Observation]
) -> list[ProjectedObservation]:
    """Project every observation's footprint onto its feature.

    Args:
        region: The projected feature the footprints are cut to.
        observations: The observations to project.

    Returns:
        One projected observation per input, in the same order.
    """
    widths = _track_widths(observations)
    projected = []
    for observation in observations:
        width_m, source = widths.get(observation.pdsid, (0.0, None))
        projected.append(
            ProjectedObservation(
                pdsid=observation.pdsid,
                ihid=observation.ihid,
                iid=observation.iid,
                pt=observation.pt,
                start=observation.start,
                stop=observation.stop,
                shape=region.footprint(footprints.parse(observation.wkt), width_m),
                width_km=width_m / 1000.0 if source else None,
                width_source=source,
            )
        )
    return projected


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

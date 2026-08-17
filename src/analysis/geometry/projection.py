"""Turning stored observations into projected ground on their feature."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from shapely import from_wkt

from analysis.geometry import footprints
from analysis.geometry.region import FeatureRegion
from analysis.utils import geodesy, swath
from models.job import Job
from models.observation import LoadedSet, Observation, ProjectedObservation
from storage import caching, records


def load_projected(
    job: Job,
) -> tuple[LoadedSet[ProjectedObservation], FeatureRegion] | None:
    """Load one set's projected footprints, from the cache when it is valid.

    A cache hit reports no discards. Only a set that yielded something is ever
    cached, so the sets whose discards matter are always read afresh.

    Args:
        job: The instrument set being computed.

    Returns:
        The projected set and the region it was measured against, or None when
        the set holds no records.
    """
    cached = caching.load(job.geometry_path, job.source)
    if cached is not None:
        return cached, FeatureRegion(cached.feature)
    loaded = records.load_set(job.source)
    if loaded is None:
        return None
    region = FeatureRegion(loaded.feature)
    projected, missed = project(region, loaded.observations)
    if projected:
        caching.save(job.geometry_path, loaded.feature, loaded.set_key, projected)
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
    region: FeatureRegion, observations: Sequence[Observation]
) -> tuple[list[ProjectedObservation], int]:
    """Project every observation's footprint onto its feature.

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

    Args:
        wkt: The footprint as well-known text.

    Returns:
        The summed length in metres.
    """
    total = 0.0
    parts, _ = footprints.single_parts(np.asarray([from_wkt(wkt)], dtype=object))
    for part in parts:
        if part.geom_type != "LineString":
            continue
        coords = np.asarray(part.coords)
        total += geodesy.haversine_length(coords[:, 0], coords[:, 1])
    return total

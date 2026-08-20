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
from storage import records


def load_projected(
    job: Job,
) -> tuple[LoadedSet[ProjectedObservation], FeatureRegion] | None:
    """Project one set's stored footprints onto its feature.

    Args:
        job: The instrument set being computed.

    Returns:
        The projected set and the region it was measured against, or None when
        the set holds no records.
    """
    loaded = records.load_set(job.source)
    if loaded is None:
        return None
    region = FeatureRegion(loaded.feature)
    projected, missed = project(region, loaded.observations)
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
    resolved = _track_widths(observations)
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
) -> list[tuple[float, str | None]]:
    """Derive a swath width for every ground track among the observations.

    Args:
        observations: The observations to inspect.

    Returns:
        One (width in metres, source) pair per observation, in the order they
        were given, carrying no width and no source for the footprints that
        already enclose area.
    """
    tracks = [
        position
        for position, observation in enumerate(observations)
        if observation.is_track
    ]
    widths: list[tuple[float, str | None]] = [(0.0, None)] * len(observations)
    if not tracks:
        return widths
    resolved = swath.resolve_widths(
        [
            (_track_length(observations[at].wkt), observations[at].duration_s)
            for at in tracks
        ]
    )
    for position, width in zip(tracks, resolved, strict=True):
        widths[position] = width
    return widths


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

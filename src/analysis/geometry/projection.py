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
        np.asarray([width or 0.0 for width in resolved], dtype=float),
    )
    projected = []
    missed = 0
    for observation, width_m, shape in zip(observations, resolved, shapes, strict=True):
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
                width_km=width_m / 1000.0 if width_m is not None else None,
            )
        )
    return projected, missed


def _track_widths(observations: Sequence[Observation]) -> list[float | None]:
    """Derive a swath width for every ground track among the observations.

    A track implies a swath only through the speed its length and its elapsed
    time give, so one carrying neither cannot be widened and is left without a
    width, which drops it as unmeasurable rather than guessing one for it.

    Args:
        observations: The observations to inspect.

    Returns:
        One width in metres per observation, in the order they were given, and
        None for the footprints that already enclose area.
    """
    widths: list[float | None] = [None] * len(observations)
    for position, observation in enumerate(observations):
        if not observation.is_track or observation.duration_s <= 0.0:
            continue
        length = _track_length(observation.wkt)
        if length > 0.0:
            widths[position] = swath.track_width(length, observation.duration_s)
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

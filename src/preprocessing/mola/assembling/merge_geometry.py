"""Checking both planes of a tile fall on one grid, and joining them there."""

from __future__ import annotations

import numpy as np

from preprocessing.mola.loaders import geometry
from preprocessing.mola.models.observation import MolaObservation
from preprocessing.mola.models.sample import MolaSample

# How far two grids may sit apart and still be read as the same one, in degrees.
TOLERANCE = 1e-9


def merge_geometry(observation: MolaObservation) -> MolaSample:
    """Join both planes of one tile onto the grid they share.

    Args:
        observation: The tile to read, both planes loaded.

    Returns:
        The joined sample, its two planes on one grid.

    Raises:
        ValueError: When the two planes are not on the same grid, or when that
            grid does not reach the corners its label claims.
    """
    height, shots = observation.topography, observation.counts
    for axis, first, second in (
        ("latitude", height.latitude, shots.latitude),
        ("longitude", height.longitude, shots.longitude),
    ):
        if first.shape != second.shape or not np.allclose(
            first, second, atol=TOLERANCE
        ):
            raise ValueError(
                f"{observation.identifier} places its two planes at a different {axis}."
            )
    _check_corners(observation)
    return MolaSample(
        observation.identifier,
        height.values,
        shots.values,
        height.latitude,
        height.longitude,
        observation.resolution,
    )


def _check_corners(observation: MolaObservation) -> None:
    """Refuse a grid whose pixels do not reach the corners its label claims.

    Args:
        observation: The tile to check, both planes loaded.

    Returns:
        None.

    Raises:
        ValueError: When a plane covers something other than its label says.
    """
    for plane in observation.planes.values():
        step = 1.0 / float(plane.label["MAP_RESOLUTION"])
        reached = geometry.bounds(plane.latitude, plane.longitude, step)
        claimed = tuple(
            float(plane.label[key])
            for key in (
                "MINIMUM_LATITUDE",
                "MAXIMUM_LATITUDE",
                "WESTERNMOST_LONGITUDE",
                "EASTERNMOST_LONGITUDE",
            )
        )
        if not np.allclose(reached, claimed, atol=TOLERANCE):
            raise ValueError(
                f"{observation.identifier} reads its {plane.kind} over "
                f"{reached}, where its label claims {claimed}."
            )

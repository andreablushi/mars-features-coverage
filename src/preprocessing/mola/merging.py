"""Checking both planes of a tile fall on one grid, and joining them there."""

from __future__ import annotations

import numpy as np

from preprocessing.common import grids
from preprocessing.mola import geometry
from preprocessing.mola.models.observation import MolaObservation
from preprocessing.mola.models.sample import MolaSample

# How far two grids may sit apart and still be read as the same one, in degrees.
TOLERANCE = 1e-9

# The corners a label claims, in the order `grids.bounds` reaches them.
CORNERS = (
    "MINIMUM_LATITUDE",
    "MAXIMUM_LATITUDE",
    "WESTERNMOST_LONGITUDE",
    "EASTERNMOST_LONGITUDE",
)


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
    for plane in observation.planes.values():
        step = geometry.pixel(plane.label)
        grids.check_bounds(
            grids.bounds(plane.latitude, plane.longitude, step),
            tuple(float(plane.label[key]) for key in CORNERS),
            TOLERANCE,
            f"{observation.identifier} {plane.kind}",
        )
    return MolaSample(
        observation.identifier,
        height.values,
        shots.values,
        height.latitude,
        height.longitude,
        observation.resolution,
    )

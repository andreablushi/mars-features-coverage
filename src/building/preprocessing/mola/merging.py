"""Joining both planes of a tile onto the grid the archive publishes them on."""

from __future__ import annotations

from building.preprocessing.mola.models.observation import MolaObservation
from building.preprocessing.mola.models.sample import MolaSample


def merge_geometry(observation: MolaObservation) -> MolaSample:
    """Join both planes of one tile onto the grid they share.

    Args:
        observation: The tile to read, both planes loaded.

    Returns:
        The joined sample, its two planes on one grid.
    """
    height, shots = observation.topography, observation.counts
    return MolaSample(
        observation.identifier,
        height.values,
        shots.values,
        height.latitude,
        height.longitude,
        observation.resolution,
    )

"""Choosing which detector's geometry describes the joined cube."""

from __future__ import annotations

import numpy as np

from preprocessing.crism.models.observation import CrismObservation


def merge_geometry(observation: CrismObservation, columns: np.ndarray) -> np.ndarray:
    """Return the backplanes for the columns both detectors kept.

    Args:
        observation: The observation to read, cleaned or not.
        columns: True for each sample both detectors kept.

    Returns:
        The backplanes as lines by columns by 14.
    """
    return observation.infrared.geometry[:, columns]


def disagreement(observation: CrismObservation) -> np.ndarray:
    """Return how far the two geometries sit apart, per backplane.

    Args:
        observation: The observation to read.

    Returns:
        The largest absolute difference in each of the 14 backplanes.
    """
    infrared, visible = observation.infrared.geometry, observation.visible.geometry
    apart = np.abs(infrared - visible)
    real = (np.abs(infrared) < 1e4) & (np.abs(visible) < 1e4)
    return np.array(
        [
            apart[..., i][real[..., i]].max() if real[..., i].any() else np.nan
            for i in range(apart.shape[2])
        ]
    )

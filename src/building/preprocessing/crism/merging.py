"""Joining the visible and infrared halves, and the geometry beside them."""

from __future__ import annotations

import numpy as np

from building.preprocessing.crism.cleaning import bands_calibration
from building.preprocessing.crism.models.observation import CrismObservation
from building.preprocessing.crism.models.sample import CrismSample


def merge_detectors(observation: CrismObservation) -> CrismSample:
    """Join both detectors of a cleaned observation into one cube.

    Args:
        observation: The observation, already through `clean.clean`, so each
            detector carries the mask saying what it kept.

    Returns:
        The joined sample, its bands ascending in wavelength.

    Raises:
        ValueError: When the observation has not been cleaned.
    """
    visible, infrared = observation.visible, observation.infrared
    if visible.mask is None or infrared.mask is None:
        raise ValueError(f"{observation.identifier} has not been cleaned.")

    # Only the samples neither detector refused, which is one unbroken run.
    columns = ~(visible.mask.columns | infrared.mask.columns)

    cubes, tables = [], []
    for detector in (visible, infrared):
        bands = ~detector.mask.bands
        cubes.append(detector.cube[:, columns][:, :, bands])
        tables.append(detector.wavelengths[columns][:, bands])

    cube = np.concatenate(cubes, axis=2)
    table = np.concatenate(tables, axis=1)
    # The two overlap around a micron, so ordering is a sort and not a join.
    order = np.argsort(bands_calibration.centres(table))
    return CrismSample(
        observation.identifier,
        cube[:, :, order],
        table[:, order],
        merge_geometry(observation, columns),
        np.flatnonzero(columns),
    )


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

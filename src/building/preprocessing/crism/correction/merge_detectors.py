"""Joining the visible and infrared halves, and the geometry beside them."""

from __future__ import annotations

import numpy as np

from building.preprocessing.crism.correction import bands_calibration
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
        observation.infrared.geometry[:, columns],
        np.flatnonzero(columns),
    )

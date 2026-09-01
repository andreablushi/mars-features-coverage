"""Joining the visible and infrared halves into one spectrum."""

from __future__ import annotations

import numpy as np

from preprocessing.crism.assembling.merge_geometry import merge_geometry
from preprocessing.crism.fetching import bands_calibration
from preprocessing.crism.models.observation import CrismObservation
from preprocessing.crism.models.sample import Sample


def merge_detectors(observation: CrismObservation) -> Sample:
    """Join both detectors of a cleaned observation into one cube.

    Args:
        observation: The observation, already through `clean.clean`, so each
            detector carries the mask saying what it kept.

    Returns:
        The joined sample, its bands ascending in wavelength.

    Raises:
        ValueError: When the observation has not been cleaned, or the two
            detectors do not share a grid.
    """
    visible, infrared = observation.visible, observation.infrared
    if visible.mask is None or infrared.mask is None:
        raise ValueError(f"{observation.identifier} has not been cleaned.")
    if visible.cube.shape[0] != infrared.cube.shape[0]:
        raise ValueError(
            f"{observation.identifier} has {visible.cube.shape[0]} visible lines "
            f"and {infrared.cube.shape[0]} infrared ones."
        )

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
    return Sample(
        observation.identifier,
        cube[:, :, order],
        table[:, order],
        merge_geometry(observation, columns),
        np.flatnonzero(columns),
    )

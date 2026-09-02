"""Turning one downloaded CRISM observation into a cube fit to compute on."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from building.preprocessing.crism import reading
from building.preprocessing.crism.cleaning import (
    atmospheric,
    bands_calibration,
    despiking,
    destriping,
    masking,
    ratioing,
)
from building.preprocessing.crism.models.observation import CrismObservation


def clean(identifier: str) -> CrismObservation:
    """Read one observation and refuse everything in it that is not measured.

    Args:
        identifier: The observation, whose files must already be in the cache
            that `download.fetch` puts them in.

    Returns:
        The observation with each detector's cube filled where it was not
        measured and its mask set beside it.

    Raises:
        FileNotFoundError: When any file the observation needs is missing.
        ValueError: When a window keeps no band of a cube.
    """
    observation = reading.read(identifier)
    detectors = {}
    for name, detector in observation.detectors.items():
        cube, mask = masking.bad_pixels(
            detector.cube, detector.wavelengths, detector.name
        )
        cube, mask = atmospheric.remove_atmospheric_bands(
            cube, mask, detector.wavelengths, detector.name
        )
        cube, mask = destriping.remove_spike_columns(
            cube, mask, detector.wavelengths, detector.name
        )
        cube = ratioing.ratio_colmed(cube, mask.pixels)
        # Despike only the bands still in play, so the filled ones cannot pull
        # the moving median around at their edges.
        kept = ~mask.bands
        block = np.ascontiguousarray(cube[:, :, kept])
        despiking.remove_spikes(
            block, bands_calibration.centres(detector.wavelengths)[kept]
        )
        cube[:, :, kept] = block
        detectors[name] = replace(detector, cube=cube, mask=mask)
    return CrismObservation(identifier, detectors)

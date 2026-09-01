"""One CRISM observation as it comes off disk, raw and whole."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from preprocessing.crism.models.mask import Mask


@dataclass(frozen=True)
class Detector:
    """One detector's half of an observation, with its geometry beside it.

    Attributes:
        name: Which detector, `l` for infrared or `s` for visible.
        cube: The I/F values as lines by samples by bands, its bands ascending
            in wavelength and its uncalibrated columns and bands NaN.
        label: The parsed label of that half.
        wavelengths: The centre wavelength in nm of every column and band, as
            columns by bands, in the same order as the cube. Columns and bands
            the detector was never calibrated for hold NaN. One centre per band
            is `bands_calibration.centres` of this, not stored beside it.
        geometry: The DDR backplanes as lines by samples by 14, on the same
            grid as the cube.
        geometry_label: The parsed label of the geometry, whose BAND_NAME says
            what each backplane holds.
        mask: Where the cube was filled rather than measured, once it has been
            cleaned, and None while it is still as it was read.
    """

    name: str
    cube: np.ndarray
    label: dict[str, str]
    wavelengths: np.ndarray
    geometry: np.ndarray
    geometry_label: dict[str, str]
    mask: Mask | None = None


@dataclass(frozen=True)
class CrismObservation:
    """Both detectors of one scan, read off disk and not yet touched.

    Attributes:
        identifier: The observation id, such as msp000396ba_01_if214_trr3.
        detectors: Each detector's half, keyed by detector letter.
    """

    identifier: str
    detectors: dict[str, Detector]

    @property
    def infrared(self) -> Detector:
        """Return the L detector, which carries the infrared.

        Returns:
            The infrared half.
        """
        return self.detectors["l"]

    @property
    def visible(self) -> Detector:
        """Return the S detector, which carries the visible.

        Returns:
            The visible half.
        """
        return self.detectors["s"]

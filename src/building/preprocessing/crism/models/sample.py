"""Both detectors of one observation as a single cube."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class CrismSample:
    """One observation with its two detectors joined.

    Attributes:
        identifier: The observation id.
        cube: Lines by columns by bands, bands ascending in wavelength, holding
            only what both detectors kept.
        wavelengths: The centre wavelength of every column and band, in that
            same order.
        geometry: The backplanes on the same grid, as lines by columns by 14.
        columns: Which of the original 64 samples these columns are.
    """

    identifier: str
    cube: np.ndarray
    wavelengths: np.ndarray
    geometry: np.ndarray
    columns: np.ndarray

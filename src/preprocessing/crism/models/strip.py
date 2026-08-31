"""One CRISM multispectral survey observation, as it comes off disk."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Strip:
    """A loaded observation and everything needed to read its spectra.

    The cube keeps every detector column the instrument wrote, including the
    four MSP leaves uncalibrated, so it stays aligned with the geometry file
    that pairs with it. Those columns are marked in `columns` rather than
    dropped. Uncalibrated bands are dropped instead, since the wavelength
    table has no entry to index them by.

    Attributes:
        product_id: The observation this came from, such as msp000396ba_01_if214l_trr3.
        cube: The spectra, lines by samples by bands, ascending in wavelength.
        wavelengths: The band centres in nanometres, ascending, one per band.
        columns: Which detector columns carry a wavelength calibration.
        bands: Which bands read the ground rather than the atmosphere or the heat.
        mask: Which voxels hold no usable measurement.
        label: The PDS label, keyed as it is written.
    """

    product_id: str
    cube: np.ndarray
    wavelengths: np.ndarray
    columns: np.ndarray
    bands: np.ndarray
    mask: np.ndarray
    label: dict[str, str]

    @property
    def spacing_nm(self) -> float:
        """Return the median gap between neighbouring band centres.

        Returns:
            The spacing in nanometres, which windows given in nanometres are
            converted against.
        """
        return float(np.median(np.diff(self.wavelengths)))

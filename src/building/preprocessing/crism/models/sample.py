"""Both detectors of one observation as a single cube."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

import numpy as np

from building.preprocessing.common.cut import taken
from building.preprocessing.common.models.cut import Cut

# Which DDR backplane places a pixel. The other twelve are dropped: three carry
# the null sentinel in every pixel, four barely vary across a scan, and the rest
# are MOLA resampled onto this grid, which the MOLA tile itself holds better.
BACKPLANES = {"latitude": 3, "longitude": 4}


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

    # A pushbroom swath bends as the spacecraft flies, so every pixel carries
    # the pair its own backplanes give it.
    separable = False

    def cut(self, held: Cut) -> Self:
        """Return this observation holding only what one cut keeps.

        A swath bends as the spacecraft flies, so the box is no rectangle on it
        and the cut is the rectangle bounding what it keeps. The wavelengths run
        along the columns, so they are cut by the column axis alone.

        Args:
            held: What the feature's box keeps of it.

        Returns:
            The observation cut to it, its bands left whole.
        """
        columns = held.bounds[1]
        return type(self)(
            identifier=self.identifier,
            cube=taken(self.cube, held.bounds),
            wavelengths=self.wavelengths[columns],
            geometry=taken(self.geometry, held.bounds),
            columns=self.columns[columns],
        )

    @property
    def latitude(self) -> np.ndarray:
        """Return the latitude every pixel was measured at.

        Returns:
            Lines by columns, in degrees.
        """
        return self.geometry[:, :, BACKPLANES["latitude"]]

    @property
    def longitude(self) -> np.ndarray:
        """Return the longitude every pixel was measured at.

        Returns:
            Lines by columns, in degrees.
        """
        return self.geometry[:, :, BACKPLANES["longitude"]]

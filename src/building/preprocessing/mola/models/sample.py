"""Both planes of one MOLA tile on a single grid."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

import numpy as np

from building.preprocessing.common.cut import taken
from building.preprocessing.common.models.cut import Cut


@dataclass(frozen=True, slots=True)
class MolaSample:
    """One tile with its two planes joined onto one grid.

    Attributes:
        identifier: The tile id.
        topography: The height of the ground above the areoid in metres, as
            lines by samples.
        counts: How many shots each bin was measured with, on the same grid,
            zero where the height was interpolated rather than observed.
        latitude: The centre latitude in degrees of every line.
        longitude: The centre longitude in degrees of every sample.
        resolution: How fine the grid is, in pixels per degree.
    """

    identifier: str
    topography: np.ndarray
    counts: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    resolution: int

    # A gridded tile is simple cylindrical, so one axis places each side.
    separable = True

    def cut(self, held: Cut) -> Self:
        """Return this tile holding only what one cut keeps.

        The box is a rectangle on the grid, so both planes are cut at once by a
        range of lines and a range of samples.

        Args:
            held: What the feature's box keeps of it.

        Returns:
            The tile cut to it, how fine its grid is unchanged.
        """
        lines, samples = held.bounds
        return type(self)(
            identifier=self.identifier,
            topography=taken(self.topography, held.bounds),
            counts=taken(self.counts, held.bounds),
            latitude=self.latitude[lines],
            longitude=self.longitude[samples],
            resolution=self.resolution,
        )

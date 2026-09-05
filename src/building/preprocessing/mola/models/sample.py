"""Both planes of one MOLA tile on a single grid."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


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

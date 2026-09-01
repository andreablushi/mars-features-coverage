"""One MOLA tile as it comes off disk, raw and whole."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from preprocessing.mola.loaders.utils import naming


@dataclass(frozen=True)
class Plane:
    """One plane of a tile, with the grid it is placed on beside it.

    Attributes:
        kind: Which plane, `naming.TOPOGRAPHY` or `naming.COUNTS`.
        values: The values as lines by samples, in the type the archive stores
            them in, metres for topography and shots per bin for counts.
        label: The parsed label of that plane.
        latitude: The centre latitude in degrees of every line.
        longitude: The centre longitude in degrees of every sample.
    """

    kind: str
    values: np.ndarray
    label: dict[str, str]
    latitude: np.ndarray
    longitude: np.ndarray


@dataclass(frozen=True)
class MolaObservation:
    """Both planes of one tile, read off disk and not yet joined.

    Attributes:
        identifier: The tile id, such as 00n180hb.
        planes: Each plane, keyed by kind.
    """

    identifier: str
    planes: dict[str, Plane]

    @property
    def topography(self) -> Plane:
        """Return the plane holding the height of the ground.

        Returns:
            The topography plane.
        """
        return self.planes[naming.TOPOGRAPHY]

    @property
    def counts(self) -> Plane:
        """Return the plane holding how many shots each bin was measured with.

        Returns:
            The counts plane.
        """
        return self.planes[naming.COUNTS]

    @property
    def resolution(self) -> int:
        """Return how fine a grid the tile is written on.

        Returns:
            The pixels per degree.
        """
        return naming.resolution(self.identifier)

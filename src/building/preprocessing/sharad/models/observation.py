"""One SHARAD track as it comes off disk, raw and whole."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SharadObservation:
    """One radargram with the geometry published beside it.

    Attributes:
        identifier: The observation id, such as s_00577101.
        power: The radar backscatter power as delay samples by traces, the
            first axis running down into the ground and the second along track.
        label: The parsed label of the radargram.
        geometry: One row per radargram column, its fields named as the
            geometry label names its columns, `RADARGRAM COLUMN` among them.
        geometry_label: The parsed label of the geometry, whose COLUMN objects
            say what each field holds and in what unit.
    """

    identifier: str
    power: np.ndarray
    label: dict[str, str]
    geometry: np.recarray
    geometry_label: dict[str, str]

    @property
    def traces(self) -> int:
        """Return how many traces the radargram holds.

        Returns:
            The count of columns across track.
        """
        return int(self.power.shape[1])

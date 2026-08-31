"""What one cleaning step left behind, so the step can be looked at on its own."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Stage:
    """The cube as one step in the cleaning left it.

    Attributes:
        name: What the step did, in the order the cleaning runs it.
        cube: The spectra after the step.
        mask: Which voxels held no usable measurement after the step.
    """

    name: str
    cube: np.ndarray
    mask: np.ndarray

    def touched(self, before: Stage) -> np.ndarray:
        """Return which voxels this step moved without making unreadable.

        Only voxels readable on both sides count, so a step that masks a voxel
        registers in `lost` rather than here.

        Args:
            before: The stage this one was computed from.

        Returns:
            A boolean array, shaped like the cube, true where the value moved.
        """
        readable = np.isfinite(self.cube) & np.isfinite(before.cube)
        moved = np.zeros(self.cube.shape, dtype=bool)
        moved[readable] = self.cube[readable] != before.cube[readable]
        return moved

    def lost(self, before: Stage) -> np.ndarray:
        """Return which voxels this step made unreadable.

        Args:
            before: The stage this one was computed from.

        Returns:
            A boolean array, shaped like the cube, true where a voxel that
            could be read before this step cannot be read after it.
        """
        return self.mask & ~before.mask

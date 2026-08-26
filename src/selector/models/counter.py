"""Counting what a sliding window holds, without recounting it each step."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from selector.models.track import Track


@dataclass(slots=True)
class Counter:
    """What one window holds, kept true as the window slides along the axis.

    Attributes:
        observations_per_cell: The window's observations filling each cell, per set.
        cells_reached: How many cells of the tile each set reaches.
    """

    observations_per_cell: list[list[int]]
    cells_reached: list[int]

    @classmethod
    def empty(cls, iids: Sequence[str], grid_cells: int) -> Counter:
        """Open a counter on a window holding nothing at all.

        Args:
            iids: The instrument each set of the tile belongs to, by set.
            grid_cells: How many cells the tile holds.

        Returns:
            The counter, counting nothing.
        """
        return cls(
            observations_per_cell=[[0] * grid_cells for _ in iids],
            cells_reached=[0] * len(iids),
        )

    @classmethod
    def over(cls, track: Track, first: int, last: int) -> Counter:
        """Count afresh everything one stretch of the axis holds.

        Args:
            track: The feature's observations on one time axis.
            first: The index of the earliest observation the stretch holds.
            last: The index of the latest one.

        Returns:
            The counter, counting that stretch.
        """
        counter = cls.empty(track.iids, track.grid_cells)
        for index in range(first, last + 1):
            counter.hold(track.owners[index], track.cells[index])
        return counter

    def hold(self, owner: int, cells: Sequence[int]) -> None:
        """Take one more observation into the window.

        Args:
            owner: The instrument set the observation belongs to.
            cells: The tile's cells it fills.

        Returns:
            None.
        """
        filled = self.observations_per_cell[owner]
        fresh = 0
        for cell in cells:
            if not filled[cell]:
                fresh += 1
            filled[cell] += 1
        self.cells_reached[owner] += fresh

    def release(self, owner: int, cells: Sequence[int]) -> None:
        """Drop the oldest observation back out of the window.

        Args:
            owner: The instrument set the observation belongs to.
            cells: The tile's cells it fills.

        Returns:
            None.
        """
        filled = self.observations_per_cell[owner]
        lost = 0
        for cell in cells:
            filled[cell] -= 1
            if not filled[cell]:
                lost += 1  # ground nothing else left in the window reaches
        self.cells_reached[owner] -= lost

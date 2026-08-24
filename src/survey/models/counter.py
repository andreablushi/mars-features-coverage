"""Counting what a sliding window holds, without recounting it each step."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from survey.models.track import Track


@dataclass(slots=True)
class Counter:
    """What one window holds, kept true as the window slides along the axis.

    Attributes:
        observations_per_cell: How many of the window's observations fill each
            cell of the tile, per instrument set.
        cells_reached: How many cells of the tile each set reaches, which is
            what the window is scored on.
    """

    observations_per_cell: list[list[int]]
    cells_reached: list[int]

    @classmethod
    def empty(cls, sets: int, grid: int) -> Counter:
        """Open a counter on a window holding nothing at all.

        Args:
            sets: How many instrument sets the tile has.
            grid: How many cells the tile holds.

        Returns:
            The counter, counting nothing.
        """
        return cls([[0] * grid for _ in range(sets)], [0] * sets)

    @classmethod
    def over(cls, track: Track, first: int, last: int) -> Counter:
        """Count afresh everything one stretch of the axis holds.

        It takes bare indices rather than a window, since the search counts the
        whole record this way before it has a window to speak of.

        Args:
            track: The feature's observations on one time axis.
            first: The index of the earliest observation the stretch holds.
            last: The index of the latest one.

        Returns:
            The counter, counting that stretch.
        """
        counter = cls.empty(len(track.labels), track.grid)
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

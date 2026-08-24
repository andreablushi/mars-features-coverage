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
        instrument_of: The instrument each set belongs to, as an index, by set.
        sets_per_cell: How many of an instrument's sets reach each cell of the
            tile, per instrument.
        instruments_per_cell: How many instruments reach each cell of the tile.
        cells_together: How many cells every instrument reaches at once.
        instruments: How many instruments the tile has, which a cell has to be
            reached by all of to count as held together.
    """

    observations_per_cell: list[list[int]]
    cells_reached: list[int]
    instrument_of: list[int]
    sets_per_cell: list[list[int]]
    instruments_per_cell: list[int]
    cells_together: int
    instruments: int

    @classmethod
    def empty(cls, iids: Sequence[str], grid: int) -> Counter:
        """Open a counter on a window holding nothing at all.

        Args:
            iids: The instrument each set of the tile belongs to, by set.
            grid: How many cells the tile holds.

        Returns:
            The counter, counting nothing.
        """
        kinds = {iid: index for index, iid in enumerate(dict.fromkeys(iids))}
        return cls(
            observations_per_cell=[[0] * grid for _ in iids],
            cells_reached=[0] * len(iids),
            instrument_of=[kinds[iid] for iid in iids],
            sets_per_cell=[[0] * grid for _ in kinds],
            instruments_per_cell=[0] * grid,
            cells_together=0,
            instruments=len(kinds),
        )

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
        counter = cls.empty(track.iids, track.grid)
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
        reaching = self.sets_per_cell[self.instrument_of[owner]]
        fresh = 0
        for cell in cells:
            if not filled[cell]:
                fresh += 1
                # Ground its instrument had nowhere else in the window
                if not reaching[cell]:
                    self.instruments_per_cell[cell] += 1
                    if self.instruments_per_cell[cell] == self.instruments:
                        self.cells_together += 1
                reaching[cell] += 1
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
        reaching = self.sets_per_cell[self.instrument_of[owner]]
        lost = 0
        for cell in cells:
            filled[cell] -= 1
            if not filled[cell]:
                lost += 1  # ground nothing else left in the window reaches
                reaching[cell] -= 1
                if not reaching[cell]:
                    if self.instruments_per_cell[cell] == self.instruments:
                        self.cells_together -= 1
                    self.instruments_per_cell[cell] -= 1
        self.cells_reached[owner] -= lost

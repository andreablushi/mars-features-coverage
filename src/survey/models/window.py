"""One stretch of time the search may pick, and what can be asked of it."""

from __future__ import annotations

from dataclasses import dataclass

from survey.models.track import Track
from survey.reach import Reach


@dataclass(frozen=True, slots=True)
class Window:
    """One window, given by the observations at either end of it.

    Attributes:
        first: The index of the earliest observation the window holds.
        last: The index of the latest one.
        days: How long it lasts, from the first start time to the last.
        reach: How much ground it reaches, as the shares of their own records
            the instrument sets reach inside it, multiplied and rooted so that
            one set cannot carry the window alone.
        instruments: How many sets have an observation inside it.
    """

    first: int
    last: int
    days: float
    reach: float
    instruments: int

    def widened(self, track: Track, wanted: int = 0) -> Window:
        """Take in every observation sharing an instant with either end.

        Args:
            track: The feature's observations on one time axis.
            wanted: How many instrument sets the search is insisting on, which
                is how many its score is taken over. Nought for all of them.

        Returns:
            The same stretch of time, holding everything taken during it.
        """
        first, last = self.first, self.last
        # Expand the window to include any observations that share the same time as the first
        while first and track.times[first - 1] == track.times[first]:
            first -= 1
        while (
            last + 1 < len(track.observations)
            and track.times[last + 1] == track.times[last]
        ):
            last += 1
        if (first, last) == (self.first, self.last):
            return self
        # If the window has changed, measure the new reach and return a new Window instance
        held = Window.measure(track, first, last, wanted)
        return Window(first, last, self.days, held.mean, held.instruments)

    def shares(self, track: Track) -> dict[str, float]:
        """Work out what each instrument set reaches inside this window.

        Args:
            track: The feature's observations on one time axis.

        Returns:
            The share of its own ground each set reaches, by set name.
        """
        held = Window.measure(track, self.first, self.last)
        return dict(zip(track.labels, held.shares, strict=True))

    @staticmethod
    def measure(track: Track, first: int, last: int, wanted: int = 0) -> Reach:
        """Fill a fresh tally with everything one stretch of the axis holds.

        Args:
            track: The feature's observations on one time axis.
            first: The index of the earliest observation it holds.
            last: The index of the latest one.
            wanted: How many instrument sets the score is taken over. Nought
                for all of them.

        Returns:
            The tally, holding that stretch and nothing else.
        """
        held = Reach(track.totals, track.grid, wanted)
        for index in range(first, last + 1):
            held.hold(track.owners[index], track.cells[index])
        return held

"""One stretch of time the search may pick, and what can be asked of it."""

from __future__ import annotations

from dataclasses import dataclass

from survey import configs
from survey.models.track import Track
from survey.utils import measuring


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

    def widened(self, track: Track) -> Window:
        """Take in every observation sharing an instant with either end.

        Args:
            track: The feature's observations on one time axis.

        Returns:
            The same stretch of time, holding everything taken during it.
        """
        first, last = self.first, self.last
        # Expand the window to any observation sharing the same time as the first
        while first and track.times[first - 1] == track.times[first]:
            first -= 1
        while (
            last + 1 < len(track.observations)
            and track.times[last + 1] == track.times[last]
        ):
            last += 1
        if (first, last) == (self.first, self.last):
            return self
        # If the window has changed, measure its new reach and return a new Window
        _, seen, inside = measuring.counted(track, first, last)
        return Window(
            first,
            last,
            self.days,
            measuring.mean(seen, track.totals, configs.MIN_SETS),
            measuring.instruments(inside),
        )

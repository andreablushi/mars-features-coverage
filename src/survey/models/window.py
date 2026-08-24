"""One stretch of time the search may pick, and what can be asked of it."""

from __future__ import annotations

from dataclasses import dataclass

from survey.models.counter import Counter
from survey.models.strategy import Demands
from survey.models.track import Track
from survey.utils import scoring


@dataclass(frozen=True, slots=True)
class Window:
    """One window, given by the observations at either end of it.

    Attributes:
        first: The index of the earliest observation the window holds.
        last: The index of the latest one.
        days: How long it lasts, from the first start time to the last.
        reach: How much of the ground it reaches, as the shares each
            instrument insisted on reaches of it, multiplied and rooted so
            that one instrument cannot carry the window alone.
    """

    first: int
    last: int
    days: float
    reach: float

    def widened(self, track: Track, demands: Demands) -> Window:
        """Take in every observation sharing an instant with either end.

        A wider window holds everything the narrower one held, so it meets
        every demand that one met and is never refused a score.

        Args:
            track: The observations on one time axis.
            demands: The instruments the strategy insists on, which are the
                ones a widened window is scored over again.

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
        counter = Counter.over(track, first, last)
        return Window(
            first,
            last,
            self.days,
            scoring.scored(track, demands, counter.cells_reached),
        )

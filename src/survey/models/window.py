"""One stretch of time the search may pick, and what can be asked of it."""

from __future__ import annotations

from dataclasses import dataclass

from survey.models.track import Track
from survey.utils import measuring
from survey.utils.measuring import Counts


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
        _, seen, inside = measured(track, first, last)
        return Window(
            first,
            last,
            self.days,
            measuring.mean(seen, track.totals, wanted),
            measuring.instruments(inside),
        )

    def shares(self, track: Track) -> dict[str, float]:
        """Work out what each instrument set reaches inside this window.

        Args:
            track: The feature's observations on one time axis.

        Returns:
            The share of its own ground each set reaches, by set name.
        """
        _, seen, _ = measured(track, self.first, self.last)
        return dict(
            zip(track.labels, measuring.shares(seen, track.totals), strict=True)
        )


def measured(
    track: Track, first: int, last: int
) -> tuple[Counts, list[int], list[int]]:
    """Count afresh everything one stretch of the axis holds.

    It takes bare indices rather than a window, since the search scores the
    whole record this way before it has a window to speak of.

    Args:
        track: The feature's observations on one time axis.
        first: The index of the earliest observation it holds.
        last: The index of the latest one.

    Returns:
        The per cell counts, the cells each set reaches, and how many
        observations each set has inside.
    """
    counts, seen, inside = measuring.opened(len(track.totals), track.grid)
    for index in range(first, last + 1):
        measuring.hold(counts, seen, inside, track.owners[index], track.cells[index])
    return counts, seen, inside

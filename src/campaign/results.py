"""What the search returns: one chosen window, and the ones it beat."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Span:
    """One window, given by the observations at either end of it.

    Attributes:
        first: The index of the earliest observation the window holds.
        last: The index of the latest one.
        days: How long it lasts, from the first start time to the last.
        reach: The average share of its own ground each instrument set reaches
            inside it.
        instruments: How many sets have an observation inside it.
    """

    first: int
    last: int
    days: float
    reach: float
    instruments: int


@dataclass(frozen=True, slots=True)
class Campaign:
    """The stretch of time a feature's instruments are best studied over.

    Attributes:
        start: When the earliest observation inside it was taken.
        end: When the latest one was taken.
        days: How long it lasts.
        reach: The average share of its own ground each instrument set reaches
            inside it, counting a set that never appears as nothing.
        instruments: How many sets have an observation inside it.
        observations: How many observations it holds in total.
        shares: What share of its own ground each set reaches, by set name.
        frontier: Every window this one was chosen from, shortest first.
    """

    start: datetime
    end: datetime
    days: float
    reach: float
    instruments: int
    observations: int
    shares: dict[str, float]
    frontier: list[Span]

    @property
    def length(self) -> str:
        """Describe how long the window lasts, in units it reads well in.

        Returns:
            The length as a phrase, such as "18 hours" or "47 days".
        """
        if self.days < 1.0:
            return f"{self.days * 24.0:.0f} hours"
        if self.days < 10.0:
            return f"{self.days:.1f} days"
        return f"{self.days:,.0f} days"

    @property
    def caption(self) -> str:
        """Sum the window up in one line, for a legend or a title.

        Returns:
            Its length, how many instruments it holds, and how much of their
            ground it reaches.
        """
        return (
            f"best window: {self.length}, {self.instruments} instruments, "
            f"{self.reach:.0%} of their ground"
        )

"""What the search returns: one chosen window, and the ones it beat."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from survey.models.window import Window


@dataclass(frozen=True, slots=True)
class Survey:
    """The stretch of time a feature's instruments are best studied over.

    Attributes:
        start: When the earliest observation inside it was taken.
        end: When the latest one was taken.
        days: How long it lasts.
        reach: How much ground it reaches, as the shares of their own records
            the instrument sets reach inside it, multiplied and rooted so that
            one set cannot carry the window alone, and counting a set that
            never appears as nothing.
        instruments: How many sets have an observation inside it.
        observations: How many observations it holds in total.
        core: How many of them brought ground nothing before them in the window
            had already brought.
        knee: Whether the curve bent, and the window is the bend in it, rather
            than the longest window the curve reached.
        shares: What share of its own ground each set reaches, by set name.
        frontier: Every window this one was chosen from, shortest first.
    """

    start: datetime
    end: datetime
    days: float
    reach: float
    instruments: int
    observations: int
    core: int
    knee: bool
    shares: dict[str, float]
    frontier: list[Window]

    @property
    def redundant(self) -> int:
        """Count the observations the window would reach the same ground without.

        Returns:
            How many of its observations brought no ground of their own.
        """
        return self.observations - self.core

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
            Its length, how many instruments it holds, and what it scores.
        """
        return (
            f"best window: {self.length}, {self.instruments} instruments, "
            f"scoring {self.reach:.0%}"
        )

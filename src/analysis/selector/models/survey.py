"""The stretch of time the search picked, and the search it came out of."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from analysis.selector.models.filter import Filter
from analysis.selector.models.track import Track


@dataclass(frozen=True, slots=True)
class Survey:
    """The stretch of time one feature is best studied over.

    Attributes:
        area_km2: How much ground the feature covers.
        start: When the earliest observation inside it was taken.
        end: When the latest one was taken.
        days: How long it lasts.
        geo_mean: The insisted shares rooted together, as a share of the feature.
        kept: The observations it holds, as their places on the timeline, oldest first.
        dropped: How many were dropped from it as repeats of ground it already held.
        standing: The observations kept from outside the window, oldest first.
    """

    area_km2: float
    start: datetime
    end: datetime
    days: float
    geo_mean: float
    kept: tuple[int, ...]
    dropped: int
    standing: tuple[int, ...]

    @property
    def taken(self) -> tuple[int, ...]:
        """Name every observation the feature keeps, in time order.

        Returns:
            The window's own observations and what came from outside it,
            oldest first, each of them named once.
        """
        return tuple(sorted(set(self.kept) | set(self.standing)))


@dataclass(frozen=True, slots=True)
class Study:
    """What the search found over one feature.

    Attributes:
        criteria: What the feature was asked for.
        track: Its admissible observations on one time axis, or None where it
            holds nothing measurable.
        survey: The window it earned, or None where it earned none.
    """

    criteria: Filter
    track: Track | None
    survey: Survey | None

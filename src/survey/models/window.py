"""One stretch of time the search may pick."""

from __future__ import annotations

from dataclasses import dataclass


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

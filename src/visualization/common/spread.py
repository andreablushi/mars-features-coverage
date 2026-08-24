"""One measurement taken over many tiles, and how much they disagree."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Spread:
    """The same number read off many tiles.

    Attributes:
        mean: Their average.
        middle: Their median, which a handful of wide tiles cannot pull.
        deviation: How far they sit from the average, as the standard
            deviation, and nought when there is only one of them.
        low: The least of them.
        high: The most of them.
        counted: How many there were.
    """

    mean: float
    middle: float
    deviation: float
    low: float
    high: float
    counted: int

    @property
    def agreed(self) -> bool:
        """Report whether the tiles all read the same.

        Returns:
            True when there is nothing to spread, so the average says it all.
        """
        return self.low == self.high


def over(values: Sequence[float]) -> Spread:
    """Read one measurement off every tile that took it.

    Args:
        values: The measurement, one per tile, in any order.

    Returns:
        The spread, empty at nought where no tile took it.
    """
    if not values:
        return Spread(0.0, 0.0, 0.0, 0.0, 0.0, 0)
    return Spread(
        mean=statistics.fmean(values),
        middle=statistics.median(values),
        deviation=statistics.pstdev(values) if len(values) > 1 else 0.0,
        low=min(values),
        high=max(values),
        counted=len(values),
    )

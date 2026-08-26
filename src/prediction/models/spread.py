"""One measurement taken over many tiles, and how much they disagree."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Spread:
    """The same number read off many tiles.

    Attributes:
        mean: Their average.
        middle: Their median, which a handful of wide tiles cannot pull.
        deviation: The standard deviation, and nought where there is only one.
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

"""What the measured features hold between them, shared ground counted once."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Overlap:
    """The ground the measured features hold between them, shared ground once.

    Attributes:
        cell_km2: How much ground one cell of the grid of Mars covers.
        ground_km2: The ground the features hold, counting shared ground once.
        covered_km2: The ground each instrument reached of it, by instrument,
            counting ground it reached on two overlapping features once.
    """

    cell_km2: float
    ground_km2: float
    covered_km2: dict[str, float]

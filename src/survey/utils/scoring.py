"""Scoring a window on how much of the tile the instruments reach inside it."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.strategy import Constraints
from survey.models.track import Track


def scored(
    track: Track, constraints: Constraints, cells_reached: Sequence[int]
) -> float | None:
    """Score what a window holds, or refuse it for what it does not hold.

    Args:
        track: The observations on one time axis.
        constraints: The sets answering each one and their floors, tightest first.
        cells_reached: How many cells each set reaches inside the window.

    Returns:
        The geometric mean of what the constraints reach, or None when one fails.
    """
    product = 1
    for answers in constraints:
        # A constraint is answered by whichever instrument reaches most of its bar
        cell_count = 0
        for answering, floor in answers:
            reached = max((cells_reached[owner] for owner in answering), default=0)
            if reached < floor:
                continue
            if reached > cell_count:
                cell_count = reached
        if not cell_count:
            return None
        product *= cell_count
    geo_mean = product ** (1.0 / len(constraints)) * track.cell_km2 / track.area_km2
    return geo_mean

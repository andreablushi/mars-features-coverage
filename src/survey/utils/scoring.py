"""Scoring a window on how much of the tile the instruments reach inside it."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.strategy import Demands
from survey.models.track import Track


def scored(
    track: Track, demands: Demands, cells_reached: Sequence[int]
) -> tuple[float, int] | None:
    """Score what a window holds, or refuse it for what it does not hold.

    Args:
        track: The observations on one time axis.
        demands: The sets answering each demand and their floors, tightest first.
        cells_reached: How many cells each set reaches inside the window.

    Returns:
        How much of the ground it reaches and how many instruments answered, or None.
    """
    product = 1
    answered = 0
    for answers in demands:
        # A demand is answered by whichever instrument reaches most of its own bar
        best = 0
        for answering, floor in answers:
            reached = max((cells_reached[owner] for owner in answering), default=0)
            if reached < floor:
                continue
            answered += 1
            if reached > best:
                best = reached
        if not best:
            return None
        product *= best
    share = product ** (1.0 / len(demands)) * track.cell_km2 / track.area_km2
    return share, answered

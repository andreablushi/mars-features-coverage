"""Scoring a window on how much of the tile the instruments reach inside it."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.strategy import Demands
from survey.models.track import Track


def scored(
    track: Track, demands: Demands, cells_reached: Sequence[int]
) -> float | None:
    """Score what a window holds, or refuse it for what it does not hold.

    It computes the geometric mean of the share of the tile each demand is
    answered over, taking the best of the instruments that can answer one, and
    returns None when a demand goes unanswered because everything that could
    answer it is missing from the window or reached too little to count.

    Args:
        track: The observations on one time axis.
        demands: One entry per demand, holding the sets answering for each
            instrument that can answer it and the cells any one of them has to
            reach, tightest demand first so that a window fails on it soonest.
        cells_reached: How many cells each set reaches inside the window.

    Returns:
        How much of the ground it reaches, between zero and one, or None when
        a demand goes unanswered.
    """
    product = 1
    for answers in demands:
        # A demand is answered by whichever instrument reaches most of its own bar
        best = 0
        for answering, floor in answers:
            reached = max((cells_reached[owner] for owner in answering), default=0)
            if reached >= floor and reached > best:
                best = reached
        if not best:
            return None
        product *= best
    return product ** (1.0 / len(demands)) * track.cell_km2 / track.area_km2

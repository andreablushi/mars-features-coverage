"""Scoring a window on how much of the tile the instruments reach inside it."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.strategy import Demands
from survey.models.track import Track


def scored(
    track: Track, demands: Demands, cells_reached: Sequence[int]
) -> tuple[float, int] | None:
    """Score what a window holds, or refuse it for what it does not hold.

    It computes the geometric mean of the share of the tile each demand is
    answered over, taking the best of the instruments that can answer one, and
    returns None when a demand goes unanswered because everything that could
    answer it is missing from the window or reached too little to count.

    It counts the answering instruments beside the ground, since a demand any
    one of them meets is still better met by two. The ground alone cannot say
    so: once the best of them covers the whole tile there is no room left in
    the share for the others to show up in.

    Args:
        track: The observations on one time axis.
        demands: One entry per demand, holding the sets answering for each
            instrument that can answer it and the cells any one of them has to
            reach, tightest demand first so that a window fails on it soonest.
        cells_reached: How many cells each set reaches inside the window.

    Returns:
        How much of the ground it reaches, between zero and one, and how many
        instruments answered a demand between them, or None when a demand goes
        unanswered.
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

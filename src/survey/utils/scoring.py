"""Scoring a window on how much of the tile the instruments reach inside it."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.strategy import Demands
from survey.models.track import Track


def scored(
    track: Track, demands: Demands, cells_reached: Sequence[int]
) -> float | None:
    """Score what a window holds, or refuse it for what it does not hold.

    It computes the geometric mean of the share of the tile each instrument
    the strategy insists on reaches, taking the best set when several answer
    for one instrument, and returns None when any of them is missing from the
    window or reached too little of the ground to count.

    Args:
        track: The observations on one time axis.
        demands: The sets answering for each instrument insisted on, and the
            cells any one of them has to reach, tightest demand first so that
            a window fails on it soonest.
        cells_reached: How many cells each set reaches inside the window.

    Returns:
        How much of the ground it reaches, between zero and one, or None when
        an instrument insisted on is missing from the window or reached too
        little of the ground to count.
    """
    product = 1
    for answering, floor in demands:
        reached = max((cells_reached[owner] for owner in answering), default=0)
        if reached < floor:
            return None
        product *= reached
    return product ** (1.0 / len(demands)) * track.cell_km2 / track.area_km2

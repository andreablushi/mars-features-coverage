"""Counting what a sliding window holds, without recounting it each step."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.strategy import Demands
from survey.models.track import Track

Counts = list[list[int]]


def opened(sets: int, grid: int) -> tuple[Counts, list[int], list[int]]:
    """Open an empty count of what a window holds.

    Args:
        sets: How many instrument sets the feature has.
        grid: How many cells the feature's grid holds.

    Returns:
        The per cell counts, the cells each set reaches, and how many
        observations each set has inside.
    """
    return [[0] * grid for _ in range(sets)], [0] * sets, [0] * sets


def hold(
    counts: Counts, seen: list[int], inside: list[int], owner: int, cells: Sequence[int]
) -> None:
    """Take one more observation into the window.

    Args:
        counts: How many of the window's observations fill each cell, per set.
        seen: How many cells each set reaches, updated here.
        inside: How many observations each set has inside, updated here.
        owner: The instrument set the observation belongs to.
        cells: The feature's cells it fills.

    Returns:
        None.
    """
    count = counts[owner]
    fresh = 0
    for cell in cells:
        if not count[cell]:
            fresh += 1  # ground the window did not hold a moment ago
        count[cell] += 1
    seen[owner] += fresh
    inside[owner] += 1


def release(
    counts: Counts, seen: list[int], inside: list[int], owner: int, cells: Sequence[int]
) -> None:
    """Drop the oldest observation back out of the window.

    Args:
        counts: How many of the window's observations fill each cell, per set.
        seen: How many cells each set reaches, updated here.
        inside: How many observations each set has inside, updated here.
        owner: The instrument set the observation belongs to.
        cells: The feature's cells it fills.

    Returns:
        None.
    """
    count = counts[owner]
    lost = 0
    for cell in cells:
        count[cell] -= 1
        if not count[cell]:
            lost += 1  # ground nothing else left in the window reaches
    seen[owner] -= lost
    inside[owner] -= 1


def counted(track: Track, first: int, last: int) -> tuple[Counts, list[int], list[int]]:
    """Count afresh everything one stretch of the axis holds.

    It takes bare indices rather than a window, since the search scores the
    whole record this way before it has a window to speak of.

    Args:
        track: The feature's observations on one time axis.
        first: The index of the earliest observation it holds.
        last: The index of the latest one.

    Returns:
        The per cell counts, the cells each set reaches, and how many
        observations each set has inside.
    """
    counts, seen, inside = opened(len(track.labels), track.grid)
    for index in range(first, last + 1):
        hold(counts, seen, inside, track.owners[index], track.cells[index])
    return counts, seen, inside


def instruments(inside: Sequence[int]) -> int:
    """Count the instrument sets with an observation in the window.

    Args:
        inside: How many observations each set has inside.

    Returns:
        The count.
    """
    return len(inside) - inside.count(0)


def scored(track: Track, demands: Demands, seen: Sequence[int]) -> float:
    """Score what a window holds, or refuse it for what it does not hold.

    The shares are multiplied and rooted rather than added and divided, so that
    one instrument cannot carry a window on its own. Every share is of the same
    ground, so the ground divides out of the product and is applied once at the
    end. An instrument that several sets answer for is credited with the best
    of them rather than with all of them at once.

    Args:
        track: The observations on one time axis.
        demands: The sets answering for each instrument insisted on, and the
            cells any one of them has to reach, tightest demand first so that
            a window fails on it soonest.
        seen: How many cells each set reaches inside the window.

    Returns:
        How much of the ground it reaches, between zero and one, or less than
        nothing when an instrument insisted on is missing from the window or
        reached too little of the ground to count.
    """
    product = 1
    for answering, floor in demands:
        reached = seen[answering[0]]
        if len(answering) > 1:
            reached = max(seen[owner] for owner in answering)
        if reached < floor:
            return -1.0
        product *= reached
    return product ** (1.0 / len(demands)) * track.cell_km2 / track.area_km2

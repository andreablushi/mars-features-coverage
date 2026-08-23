"""Counting what a sliding window holds, without recounting it each step."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.strategy import Floors
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


def covered(seen: Sequence[int], cell_km2: float) -> list[float]:
    """Return the ground in square kilometres each set reaches in the window.

    Args:
        seen: How many cells each set reaches inside the window.
        cell_km2: How much ground one cell covers.

    Returns:
        One ground per set, in square kilometres.
    """
    return [cells * cell_km2 for cells in seen]


def reach(track: Track, seen: Sequence[int], floors: Floors) -> float:
    """Return how much of the ground a window reaches, counting it evenly out.

    The shares are multiplied and rooted rather than added and divided, so that
    one instrument cannot carry a window on its own. An instrument with nothing
    in the window counts as zero, which is what lets the sweep trust that a
    wider window is never worse.

    Args:
        track: The feature's observations on one time axis.
        seen: How many cells each set reaches inside the window.
        floors: The sets answering for each instrument the strategy insists on,
            which are the instruments the score is taken over.

    Returns:
        The score, between zero and one.
    """
    product = 1.0
    for answering, _ in floors:
        reached = max(seen[owner] for owner in answering)
        product *= reached * track.cell_km2 / track.area_km2
    return product ** (1.0 / len(floors))

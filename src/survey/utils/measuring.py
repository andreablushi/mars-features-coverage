"""Counting what a sliding window holds, without recounting it each step."""

from __future__ import annotations

from collections.abc import Sequence

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


def instruments(inside: Sequence[int]) -> int:
    """Count the instrument sets with an observation in the window.

    Args:
        inside: How many observations each set has inside.

    Returns:
        The count.
    """
    return len(inside) - inside.count(0)


def shares(seen: Sequence[int], totals: Sequence[int]) -> list[float]:
    """Return what share of its own ground each set reaches in the window.

    Args:
        seen: How many cells each set reaches inside the window.
        totals: How many it fills across its whole record.

    Returns:
        One share per set, where 1.0 means the window holds everything that
        set ever covered of this feature.
    """
    return [held / total for held, total in zip(seen, totals, strict=True)]


def mean(seen: Sequence[int], totals: Sequence[int], wanted: int = 0) -> float:
    """Return how much ground the window reaches, counting it evenly out.

    The shares are multiplied and rooted rather than added and divided, so that
    one instrument cannot carry a window on its own. A set absent from the
    window counts as zero, which is what lets the sweep trust that a wider
    window is never worse.

    Args:
        seen: How many cells each set reaches inside the window.
        totals: How many it fills across its whole record.
        wanted: How many sets the score is taken over, best first. Nought for
            all of them.

    Returns:
        The score, between zero and one.
    """
    scored = shares(seen, totals)
    if wanted and wanted < len(scored):
        scored = sorted(scored, reverse=True)[:wanted]
    product = 1.0
    for share in scored:
        product *= share
    return product ** (1.0 / len(scored))

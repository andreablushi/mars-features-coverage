"""Which observations a window can do without, and what the rest still reach."""

from __future__ import annotations

from selector.filters import floors
from selector.models.counter import Counter
from selector.models.track import Track
from selector.models.window import Window
from selector.utils import scoring
from selector.utils.constraints import Constraints


def trimmed(
    track: Track, window: Window, constraints: Constraints, gain: int
) -> tuple[list[int], float]:
    """Drop the observations a window does not need, oldest first.

    Args:
        track: The feature's observations on one time axis.
        window: The window they are counted inside.
        constraints: The cells each instrument insisted on has to reach.
        gain: The cells an observation has to bring that its own set does not reach.

    Returns:
        The observations worth keeping, oldest first, and the mean the rest score.
    """
    # List of the observations that are kept
    kept = list(range(window.first, window.last + 1))
    # Count what the window holds in cells
    counter = Counter.over(track, window.first, window.last)
    geo_mean = scoring.scored(track, floors.met(constraints, counter.cells_reached))
    # Try to drop each observation, oldest first, and keep the rest
    for index in list(kept):
        score = _without(track, counter, constraints, index, gain)
        # If the window can do without the observation
        if score is not None:
            geo_mean = score
            kept.remove(index)
    return kept, geo_mean


def _without(
    track: Track, counter: Counter, constraints: Constraints, index: int, gain: int
) -> float | None:
    """Take one observation out of a window, unless the window needs it.

    Args:
        track: The feature's observations on one time axis.
        counter: What the window holds, which the observation is taken out of.
        constraints: The cells each instrument insisted on has to reach.
        index: The observation to try the window without.
        gain: The cells it has to bring that its own set does not already reach.

    Returns:
        The geometric mean the rest score, or None when it cannot be spared.
    """
    owner, cells = track.owners[index], track.cells[index]
    filled = counter.observations_per_cell[owner]
    if sum(1 for cell in cells if filled[cell] == 1) >= gain:
        return None
    counter.release(owner, cells)
    counts = floors.met(constraints, counter.cells_reached)
    if counts is None:
        counter.hold(owner, cells)
        return None
    return scoring.scored(track, counts)

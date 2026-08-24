"""Which observations a window can do without, and what the rest still reach."""

from __future__ import annotations

from survey import configs
from survey.models.counter import Counter
from survey.models.strategy import Demands
from survey.models.track import Track
from survey.models.window import Window
from survey.utils import scoring


def trimmed(track: Track, window: Window, demands: Demands) -> tuple[list[int], float]:
    """Drop the observations a window does not need, its ends first.

    Args:
        track: The feature's observations on one time axis.
        window: The window they are counted inside.
        demands: The cells each instrument insisted on has to reach.

    Returns:
        The observations worth keeping, oldest first, and how much of the tile
        they reach between them.
    """
    # List of the observations that are kept
    kept = list(range(window.first, window.last + 1))
    # Count what the window holds in cells
    counter = Counter.empty(track.iids, track.grid)
    for index in kept:
        counter.hold(track.owners[index], track.cells[index])
    reach = window.reach
    # An end is tried before the middle, since only an end costs the window time
    while len(kept) > 2:
        ends = sorted(
            (
                (track.times[kept[1]] - track.times[kept[0]], 0),
                (track.times[kept[-1]] - track.times[kept[-2]], -1),
            ),
            reverse=True,
        )
        for _, edge in ends:
            score = _without(track, counter, demands, kept[edge])
            # If the window can do without the observation
            if score is not None:
                reach = score
                kept.pop(edge)
                break
        else:
            break
    # The middle costs the window no time at all, so what is spare there goes
    for index in kept[1:-1]:
        score = _without(track, counter, demands, index)
        if score is not None:
            reach = score
            kept.remove(index)
    return kept, reach


def _without(
    track: Track, counter: Counter, demands: Demands, index: int
) -> float | None:
    """Take one observation out of a window, unless the window needs it.

    Args:
        track: The feature's observations on one time axis.
        counter: What the window holds, which the observation is taken out of
            and put back when it turns out to be needed.
        demands: The cells each instrument insisted on has to reach.
        index: The observation to try the window without.

    Returns:
        How much of the tile the rest reach, or None when the observation
        brought ground of its own or a demand would go with it.
    """
    owner, cells = track.owners[index], track.cells[index]
    filled = counter.observations_per_cell[owner]
    if sum(1 for cell in cells if filled[cell] == 1) >= configs.MIN_GAIN_CELLS:
        return None
    counter.release(owner, cells)
    score = scoring.scored(track, demands, counter.cells_reached)
    if score is None:
        counter.hold(owner, cells)
    return score

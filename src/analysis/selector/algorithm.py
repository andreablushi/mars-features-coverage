"""The window worth the most, once a day of waiting is priced against ground."""

from __future__ import annotations

from bisect import bisect_left

from analysis.selector import configs
from analysis.selector.filters import floors, redundancy, timeless
from analysis.selector.models.counter import Counter
from analysis.selector.models.strategy import Constraints, Strategy
from analysis.selector.models.survey import Survey
from analysis.selector.models.track import Track
from analysis.selector.models.window import Window
from analysis.selector.utils import scoring


def search(track: Track, strategy: Strategy) -> Survey | None:
    """Search a timeline for the window the ground is best studied over.

    Args:
        track: The admissible observations on one time axis.
        strategy: The strategy read against the feature, holding what a tile is asked.

    Returns:
        The chosen window, or None when no window is worth keeping.
    """
    # What the strategy asks of this tile, worked out once when it was read
    windowed, standing = strategy.windowed[track.tile], strategy.standing[track.tile]
    # What time cannot change is asked of the whole record rather than a window
    if standing:
        whole = Counter.over(track, 0, len(track.observations) - 1)
        if floors.met(standing, whole.cells_reached) is None:
            return None
    # Take the best window
    picked = _best(track, windowed, strategy)
    if picked is None:
        return None
    # Clean up the record to only what is worth keeping, and report reached
    kept, geo_mean = redundancy.trimmed(track, picked, windowed, configs.GAIN)
    return Survey(
        tile=track.tile,
        area_km2=track.area_km2,
        start=track.observations[kept[0]].t_start,
        end=track.observations[kept[-1]].t_start,
        days=track.times[kept[-1]] - track.times[kept[0]],
        geo_mean=geo_mean,
        kept=tuple(kept),
        dropped=picked.last - picked.first + 1 - len(kept),
        standing=timeless.kept(track, strategy.timeless),
    )


def _best(track: Track, windowed: Constraints, strategy: Strategy) -> Window | None:
    """Take the window worth the most, at the price a day of waiting costs.

    Args:
        track: The admissible observations on one time axis.
        windowed: The cells each instrument insisted on has to reach.
        strategy: What the window is asked for, which caps how long it runs.

    Returns:
        The window worth the most, or None when no window is worth keeping.
    """
    span_days = strategy.span_days
    looked = _looked_before(track)
    reached = [0] * len(track.iids)
    best: Window | None = None
    worth = float("-inf")
    # Loop over the observation as bound of the window
    for left in range(len(track.observations)):
        for owner in range(len(reached)):
            reached[owner] = 0
        for right in range(left, len(track.observations)):
            days = track.times[right] - track.times[left]
            if days > span_days:
                break
            fresh = bisect_left(looked[right], left)
            if not fresh:
                continue
            reached[track.owners[right]] += fresh
            counts = floors.met(windowed, reached)
            if counts is None:
                continue  # the window does not hold what the strategy asks
            paid = scoring.scored(track, counts, days)
            if paid > worth:
                best, worth = Window(left, right, days), paid
    return best


def _looked_before(track: Track) -> list[list[int]]:
    """Say where each observation's own set last reached each cell it fills.

    Args:
        track: The admissible observations on one time axis.

    Returns:
        For each observation, where on the axis its own set last reached each of
        its cells, or -1 for a cell that set had never reached, in order.
    """
    seen: list[dict[int, int]] = [{} for _ in track.iids]
    looked: list[list[int]] = []
    for index, owner in enumerate(track.owners):
        last = seen[owner]
        before: list[int] = []
        for cell in track.cells[index].tolist():
            before.append(last.get(cell, -1))
            last[cell] = index
        before.sort()
        looked.append(before)
    return looked

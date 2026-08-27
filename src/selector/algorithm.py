"""The window worth the most, once a day of waiting is priced against ground."""

from __future__ import annotations

from selector.filters import floors, redundancy, timeless
from selector.models.counter import Counter
from selector.models.strategy import Strategy
from selector.models.survey import Survey
from selector.models.track import Track
from selector.models.window import Window
from selector.utils import constraints, scoring
from selector.utils.constraints import Constraints


def search(track: Track, strategy: Strategy) -> Survey | None:
    """Search a timeline for the window the ground is best studied over.

    Args:
        track: The admissible observations on one time axis.
        strategy: Which instruments the window has to hold, and how much ground each.

    Returns:
        The chosen window, or None when no window is worth keeping.
    """
    # Pick up the strategy's requirements, every one of which is mandatory
    windowed, standing = constraints.read_strategy(
        strategy, track.iids, track.area_km2, track.cell_km2
    )
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
    kept, geo_mean = redundancy.trimmed(track, picked, windowed, strategy.gain)
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
    best: Window | None = None
    worth = float("-inf")
    # Loop over the observation as bound of the window
    for left in range(len(track.observations)):
        counter = Counter.empty(track.iids, track.grid_cells)
        for right in range(left, len(track.observations)):
            days = track.times[right] - track.times[left]
            if days > span_days:
                break
            counter.hold(track.owners[right], track.cells[right])
            counts = floors.met(windowed, counter.cells_reached)
            if counts is None:
                continue  # the window does not hold what the strategy asks
            paid = scoring.scored(track, counts, days)
            if paid > worth:
                best, worth = Window(left, right, days), paid
    return best

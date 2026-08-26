"""The window worth the most, once a day of waiting is priced against ground."""

from __future__ import annotations

from survey import configs
from survey.filters import redundancy, timeless
from survey.models.counter import Counter
from survey.models.strategy import Constraints, Strategy
from survey.models.survey import Survey
from survey.models.track import Track
from survey.models.window import Window
from survey.utils import scoring


def search(track: Track, strategy: Strategy) -> Survey | None:
    """Search a timeline for the window the ground is best studied over.

    Args:
        track: The admissible observations on one time axis.
        strategy: Which instruments the window has to hold, and how much ground each.

    Returns:
        The chosen window, or None when no window is worth keeping.
    """
    # Pick up the strategy's requirements, every one of which is mandatory
    constraints, standing = strategy.floors(track.iids, track.area_km2, track.cell_km2)
    # What time cannot change is asked of the whole record rather than a window
    if standing:
        whole = Counter.over(track, 0, len(track.observations) - 1)
        if scoring.scored(track, standing, whole.cells_reached) is None:
            return None
    picked = _best(track, constraints, strategy)
    if picked is None:
        return None
    kept, geo_mean = redundancy.trimmed(track, picked, constraints, strategy.gain)
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


def _best(track: Track, constraints: Constraints, strategy: Strategy) -> Window | None:
    """Take the window worth the most, at the price a day of waiting costs.

    Args:
        track: The admissible observations on one time axis.
        constraints: The cells each instrument insisted on has to reach.
        strategy: What the window is asked for, which caps how long it runs.

    Returns:
        The window worth the most, or None when no window is worth keeping.
    """
    price = 0.01 / configs.DAYS_PER_PERCENT
    span_days = strategy.span_days
    best: Window | None = None
    worth = float("-inf")
    for left in range(len(track.observations)):
        counter = Counter.empty(track.iids, track.grid)
        for right in range(left, len(track.observations)):
            days = track.times[right] - track.times[left]
            # The axis runs forwards, so nothing beyond here is short enough
            if days > span_days:
                break
            counter.hold(track.owners[right], track.cells[right])
            geo_mean = scoring.scored(track, constraints, counter.cells_reached)
            if geo_mean is None:
                continue  # the window does not hold what the strategy asks
            paid = geo_mean - price * days
            if paid > worth:
                best, worth = Window(left, right, days, geo_mean), paid
    return best

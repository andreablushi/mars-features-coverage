"""The window worth the most, once a day of waiting is priced against ground."""

from __future__ import annotations

from survey import configs
from survey.filters import redundancy
from survey.models.counter import Counter
from survey.models.strategy import Demands, Strategy
from survey.models.survey import Survey
from survey.models.track import Track
from survey.models.window import Window
from survey.utils import scoring


def search(track: Track, strategy: Strategy) -> Survey | None:
    """Search a timeline for the window the ground is best studied over.

    Args:
        track: The admissible observations on one time axis.
        strategy: Which instruments the window has to hold, and how much
            ground each of them has to reach inside it.

    Returns:
        The chosen window, or None when no window is worth keeping.
    """
    # Pick up the strategy's requirements, every one of which is mandatory
    demands, standing = strategy.floors(track.iids, track.area_km2, track.cell_km2)
    # What time cannot change is asked of the whole record rather than a window
    if standing and not _standing(track, standing):
        return None
    picked = _best(track, demands, strategy.span_days)
    if picked is None:
        return None
    kept, reach = redundancy.trimmed(track, picked, demands)
    return Survey(
        tile=track.tile,
        area_km2=track.area_km2,
        start=track.observations[kept[0]].t_start,
        end=track.observations[kept[-1]].t_start,
        days=track.times[kept[-1]] - track.times[kept[0]],
        reach=reach,
        kept=tuple(kept),
        dropped=picked.last - picked.first + 1 - len(kept),
    )


def _standing(track: Track, standing: Demands) -> bool:
    """Ask the whole record for what no window can be asked to hold.

    Args:
        track: The admissible observations on one time axis.
        standing: The cells each timeless instrument has to reach, whenever it
            reached them.

    Returns:
        True when the record answers for every one of them.
    """
    whole = Counter.over(track, 0, len(track.observations) - 1)
    return scoring.scored(track, standing, whole.cells_reached) is not None


def _best(track: Track, demands: Demands, span_days: float) -> Window | None:
    """Take the window worth the most, at the price a day of waiting costs.

    Every window the demands allow is weighed, so the one returned is the best
    there is rather than the best of a sample.

    Args:
        track: The admissible observations on one time axis.
        demands: The cells each instrument insisted on has to reach.
        span_days: How long the window may run.

    Returns:
        The window worth the most, or None when no window is worth keeping.
    """
    price = 0.01 / configs.DAYS_PER_PERCENT
    best: Window | None = None
    worth = float("-inf")
    for left in range(len(track.observations)):
        counter = Counter.empty(len(track.labels), track.grid)
        for right in range(left, len(track.observations)):
            counter.hold(track.owners[right], track.cells[right])
            reach = scoring.scored(track, demands, counter.cells_reached)
            if reach is None:
                continue  # the window does not hold what the strategy asks
            days = track.times[right] - track.times[left]
            paid = reach - price * days
            if days <= span_days and paid > worth:
                best, worth = Window(left, right, days, reach), paid
    return best

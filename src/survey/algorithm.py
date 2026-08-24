"""The shortest window worth keeping that reaches the most ground."""

from __future__ import annotations

from survey import configs
from survey.filters import redundancy
from survey.models.counter import Counter
from survey.models.strategy import Demands, Strategy
from survey.models.survey import Survey
from survey.models.track import Track
from survey.models.window import Window
from survey.utils import scoring
from utils.maths import quantities


def search(track: Track, strategy: Strategy) -> Survey | None:
    """Search a timeline for the window the ground is best studied over.

    Args:
        track: The admissible observations on one time axis.
        strategy: Which instruments the window has to hold, and how much
            ground each of them has to reach inside it.

    Returns:
        The chosen window, or None when no window is worth keeping.
    """
    # Pick up the strategy's requirements
    demands = strategy.floors(track.iids, track.area_km2, track.cell_km2)
    if demands is None:
        return None
    # Build the first window that reaches the most ground
    frontier = _frontier(track, demands)
    if not frontier:
        return None
    picked = _bend(frontier)
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


def _frontier(track: Track, demands: Demands) -> list[Window]:
    """Trace the shortest window worth keeping at every level of ground.

    Args:
        track: The admissible observations on one time axis.
        demands: The cells each instrument insisted on has to reach.

    Returns:
        One window per level of ground, shortest first, and nothing at all
        when no window is worth keeping.
    """
    # Take the maximum ground the whole record can hold as a ceiling for the windows
    whole = Counter.over(track, 0, len(track.observations) - 1)
    ceiling = scoring.scored(track, demands, whole.cells_reached)
    # If the whole record does not reach the demands, there is no window worth keeping
    if ceiling is None:
        return []
    # Keep reducing the ceiling until the window is too long to be worth keeping
    frontier: list[Window] = []
    seen: set[tuple[int, int]] = set()
    for step in range(configs.LEVELS + 1):
        found = _shortest(track, demands, ceiling * step / configs.LEVELS)
        if found is None:
            break
        found = found.widened(track, demands)
        if (found.first, found.last) not in seen:
            seen.add((found.first, found.last))
            frontier.append(found)
    return frontier


def _shortest(track: Track, demands: Demands, level: float) -> Window | None:
    """Find the shortest window worth keeping that reaches one level of ground.

    Args:
        track: The admissible observations on one time axis.
        demands: The cells each instrument insisted on has to reach.
        level: The ground the window has to reach, counted evenly.

    Returns:
        The shortest window reaching it, or None when nothing worth keeping
        reaches it inside the span the cap allows.
    """
    counter = Counter.empty(len(track.labels), track.grid)
    found: Window | None = None
    left = 0
    for right in range(len(track.observations)):
        counter.hold(track.owners[right], track.cells[right])
        while (
            score := scoring.scored(track, demands, counter.cells_reached)
        ) is not None and score >= level - configs.ROUNDING:
            days = track.times[right] - track.times[left]
            if days <= configs.MAX_SPAN_DAYS and (
                found is None or (days, -score) < (found.days, -found.reach)
            ):
                found = Window(left, right, days, score)
            counter.release(track.owners[left], track.cells[left])
            left += 1
    return found


def _bend(frontier: list[Window]) -> Window:
    """Take the window where more days stop buying much more ground.

    Args:
        frontier: The shortest window at every level of ground, shortest first.

    Returns:
        The window. Nothing above the diagonal means ground is speeding up
        rather than running out, so there is nothing to gain by stopping early
        and every day the cap allows is taken.
    """
    cost = quantities.unit([span.days for span in frontier])
    gain = quantities.unit([span.reach for span in frontier])
    lift = [ground - days for days, ground in zip(cost, gain, strict=True)]
    turn = max(range(len(lift)), key=lift.__getitem__)
    return frontier[turn] if lift[turn] > 0.0 else frontier[-1]

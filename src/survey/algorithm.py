"""The shortest window worth keeping that reaches the most ground."""

from __future__ import annotations

from survey import configs
from survey.filters import redundancy
from survey.models.strategy import Demands, Strategy
from survey.models.survey import Survey
from survey.models.track import Track
from survey.models.window import Window
from survey.utils import measuring
from utils.maths import quantities


def search(track: Track, strategy: Strategy) -> Survey | None:
    """Search a timeline for the window the ground is best studied over.

    Only a window the dataset would keep is ever weighed: every instrument the
    strategy insists on is in it, each over as much ground as it is asked for,
    and it runs no longer than the cap. Nothing is picked and judged
    afterwards, so a record holding no such window is left without one rather
    than given the best of what would have been thrown away.

    Args:
        track: The admissible observations on one time axis.
        strategy: Which instruments the window has to hold, and how much
            ground each of them has to reach inside it.

    Returns:
        The chosen window, or None when no window is worth keeping.
    """
    demands = strategy.floors(track.iids, track.area_km2, track.cell_km2)
    if demands is None:
        return None  # an instrument the strategy insists on never came here
    frontier = _frontier(track, demands)
    if not frontier:
        return None
    picked, knee = _bend(frontier)
    return Survey(
        tile=track.tile,
        area_km2=track.area_km2,
        start=track.observations[picked.first].t_start,
        end=track.observations[picked.last].t_start,
        days=picked.days,
        reach=picked.reach,
        instruments=picked.instruments,
        observations=picked.last - picked.first + 1,
        core=redundancy.trimming(track, picked),
        knee=knee,
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
    # Rungs climb towards what the whole record reaches, so the curve is
    # sampled evenly whatever the ground can offer.
    _, whole, _ = measuring.counted(track, 0, len(track.observations) - 1)
    ceiling = measuring.scored(track, demands, whole)
    if ceiling < 0.0:
        return []  # what the whole record cannot hold, no window inside it can
    frontier: list[Window] = []
    seen: set[tuple[int, int]] = set()
    for step in range(configs.LEVELS + 1):
        found = _shortest(track, demands, ceiling * step / configs.LEVELS)
        if found is None:
            break  # asking for more ground can only ever ask for more days
        found = found.widened(track, demands)  # a tie in time is free
        if (found.first, found.last) not in seen:
            seen.add((found.first, found.last))
            frontier.append(found)
    return frontier


def _shortest(track: Track, demands: Demands, level: float) -> Window | None:
    """Find the shortest window worth keeping that reaches one level of ground.

    The window is slid along the axis, widened to the right and tightened from
    the left for as long as it is still worth keeping, which it can only stop
    being as it tightens.

    Args:
        track: The admissible observations on one time axis.
        demands: The cells each instrument insisted on has to reach.
        level: The ground the window has to reach, counted evenly.

    Returns:
        The shortest window reaching it, or None when nothing worth keeping
        reaches it inside the span the cap allows.
    """
    counts, reached, inside = measuring.opened(len(track.labels), track.grid)
    found: Window | None = None
    left = 0
    for right in range(len(track.observations)):
        measuring.hold(counts, reached, inside, track.owners[right], track.cells[right])
        while (
            scored := measuring.scored(track, demands, reached)
        ) >= level - configs.ROUNDING:
            days = track.times[right] - track.times[left]
            if days <= configs.MAX_SPAN_DAYS and (
                found is None or (days, -scored) < (found.days, -found.reach)
            ):
                found = Window(left, right, days, scored, measuring.instruments(inside))
            measuring.release(
                counts, reached, inside, track.owners[left], track.cells[left]
            )
            left += 1
    return found


def _bend(frontier: list[Window]) -> tuple[Window, bool]:
    """Take the window where more days stop buying much more ground.

    Both axes are rescaled to nought and one, and the point sitting furthest
    above the diagonal joining the ends of the curve is the bend in it.

    Args:
        frontier: The shortest window at every level of ground, shortest first.

    Returns:
        The window and whether the curve bent at all. Nothing above the
        diagonal means ground is speeding up rather than running out, so there
        is nothing to gain by stopping early and every day the cap allows is
        taken.
    """
    cost = quantities.unit([span.days for span in frontier])
    gain = quantities.unit([span.reach for span in frontier])
    lift = [ground - days for days, ground in zip(cost, gain, strict=True)]
    turn = max(range(len(lift)), key=lift.__getitem__)
    knee = lift[turn] > 0.0
    return frontier[turn] if knee else frontier[-1], knee

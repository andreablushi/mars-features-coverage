"""The shortest window worth keeping that reaches the most ground."""

from __future__ import annotations

from survey import configs
from survey.filters import redundancy
from survey.models.survey import Survey
from survey.models.track import Track
from survey.models.window import Window
from survey.utils import measuring
from utils.maths import quantities


def search(track: Track) -> Survey | None:
    """Search a timeline for the window the feature is best studied over.

    Only a window the dataset would keep is ever weighed: it holds a sounder
    track, it holds instruments enough to learn from, and it runs no longer
    than the cap. Nothing is picked and judged afterwards, so a feature whose
    record holds no such window is left without one rather than given the
    best of what would have been thrown away.

    Args:
        track: The feature's admissible observations on one time axis.

    Returns:
        The chosen window, or None when no window is worth keeping.
    """
    frontier = _frontier(track)
    if not frontier:
        return None
    picked, knee = _bend(frontier)
    return Survey(
        start=track.observations[picked.first].t_start,
        end=track.observations[picked.last].t_start,
        days=picked.days,
        reach=picked.reach,
        instruments=picked.instruments,
        observations=picked.last - picked.first + 1,
        core=redundancy.trimming(track, picked),
        knee=knee,
    )


def _frontier(track: Track) -> list[Window]:
    """Trace the shortest window worth keeping at every level of ground.

    Args:
        track: The feature's admissible observations on one time axis.

    Returns:
        One window per level of ground, shortest first, and nothing at all
        when no window is worth keeping.
    """
    # Rungs climb towards what the whole record reaches, so the curve is
    # sampled evenly whatever the feature can offer.
    _, whole, _ = measuring.counted(track, 0, len(track.observations) - 1)
    ceiling = measuring.mean(whole, track.totals, configs.MIN_SETS)
    frontier: list[Window] = []
    seen: set[tuple[int, int]] = set()
    for step in range(configs.LEVELS + 1):
        found = _shortest(track, ceiling * step / configs.LEVELS)
        if found is None:
            break  # asking for more ground can only ever ask for more days
        found = found.widened(track)  # a tie in time is free
        if (found.first, found.last) not in seen:
            seen.add((found.first, found.last))
            frontier.append(found)
    return frontier


def _shortest(track: Track, level: float) -> Window | None:
    """Find the shortest window worth keeping that reaches one level of ground.

    The window is slid along the axis, widened to the right and tightened from
    the left for as long as it is still worth keeping, which it can only stop
    being as it tightens.

    Args:
        track: The feature's admissible observations on one time axis.
        level: The ground the window has to reach, counted evenly.

    Returns:
        The shortest window reaching it, or None when nothing worth keeping
        reaches it inside the span the cap allows.
    """
    counts, reached, inside = measuring.opened(len(track.totals), track.grid)
    found: Window | None = None
    sounders, left = 0, 0
    for right in range(len(track.observations)):
        measuring.hold(counts, reached, inside, track.owners[right], track.cells[right])
        sounders += track.sounder[right]
        while sounders and _kept(track, reached, inside, level):
            days = track.times[right] - track.times[left]
            scored = measuring.mean(reached, track.totals, configs.MIN_SETS)
            if days <= configs.MAX_SPAN_DAYS and (
                found is None or (days, -scored) < (found.days, -found.reach)
            ):
                found = Window(left, right, days, scored, measuring.instruments(inside))
            measuring.release(
                counts, reached, inside, track.owners[left], track.cells[left]
            )
            sounders -= track.sounder[left]
            left += 1
    return found


def _kept(track: Track, reached: list[int], inside: list[int], level: float) -> bool:
    """Report whether what a window holds is worth keeping at one level.

    Args:
        track: The feature's admissible observations on one time axis.
        reached: How many cells each set reaches inside the window.
        inside: How many observations each set has inside it.
        level: The ground it has to reach, counted evenly.

    Returns:
        True when it holds instruments enough and reaches that much ground.
    """
    if measuring.instruments(inside) < configs.MIN_SETS:
        return False
    scored = measuring.mean(reached, track.totals, configs.MIN_SETS)
    return scored >= level - configs.ROUNDING


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

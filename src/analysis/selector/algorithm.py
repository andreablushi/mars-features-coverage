"""The window worth the most, once a day of waiting is priced against ground."""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Sequence

from analysis.coverage import ground
from analysis.selector import configs
from analysis.selector.filters import redundancy, timeless
from analysis.selector.filters.coverage_constraints import coverage_constraints
from analysis.selector.models.counter import Counter
from analysis.selector.models.filter import Constraints, Filter
from analysis.selector.models.survey import Survey
from analysis.selector.models.track import Track
from analysis.selector.models.window import Window

_PRICE_PER_DAY = 0.01 / configs.DAYS_PER_PERCENT


def search(track: Track, criteria: Filter) -> Survey | None:
    """Search a timeline for the window the ground is best studied over.

    Args:
        track: The admissible observations on one time axis.
        criteria: The filter read against the feature, holding what it is asked.

    Returns:
        The chosen window, or None when no window is worth keeping.
    """
    # What the filter asks of this feature, worked out once when it was read
    windowed, standing = criteria.windowed, criteria.standing
    # What time cannot change is asked of the whole record rather than a window
    if standing:
        whole = Counter.over(track, 0, len(track.observations) - 1)
        if coverage_constraints(standing, whole.cells_reached) is None:
            return None
    # Take the best window
    picked = _best(track, windowed, criteria)
    if picked is None:
        return None
    # Clean up the record to only what is worth keeping, and report reached
    kept, reached = redundancy.trimmed(track, picked, windowed, configs.GAIN)
    return Survey(
        area_km2=track.grid.area_km2,
        start=track.observations[kept[0]].t_start,
        end=track.observations[kept[-1]].t_start,
        days=track.times[kept[-1]] - track.times[kept[0]],
        geo_mean=_scored(track, reached),
        kept=tuple(kept),
        standing=timeless.fresh_looks(track, criteria.timeless),
    )


def _best(track: Track, windowed: Constraints, criteria: Filter) -> Window | None:
    """Take the window worth the most, at the price a day of waiting costs.

    Args:
        track: The admissible observations on one time axis.
        windowed: The cells each instrument insisted on has to reach.
        criteria: What the window is asked for, which caps how long it runs.

    Returns:
        The window worth the most, or None when no window is worth keeping.
    """
    span_days = criteria.span_days
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
            counts = coverage_constraints(windowed, reached)
            if counts is None:
                continue  # the window does not hold what the filter asks
            paid = _scored(track, counts, days)
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


def _scored(track: Track, counts: Sequence[int], days: float = 0.0) -> float:
    """Score what a window reaches, less what the days it runs for cost it.

    Args:
        track: The observations on one time axis.
        counts: The cells each constraint reaches, one count per constraint.
        days: How long the window runs, charged against the ground it reaches.

    Returns:
        The constraints rooted together as a share of the feature, less their days.
    """
    rooted = math.prod(counts) ** (1.0 / len(counts))
    geo_mean = ground.share(rooted, track.grid.cell_km2, track.grid.area_km2)
    return geo_mean - _PRICE_PER_DAY * days

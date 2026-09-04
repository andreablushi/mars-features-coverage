"""The Mars season one feature is best studied over, of the seasons it was seen in."""

from __future__ import annotations

import math
from collections.abc import Sequence

from analysis.coverage import ground
from analysis.selector import configs
from analysis.selector.filters import redundancy, seasons, timeless
from analysis.selector.filters.coverage_constraints import coverage_constraints
from analysis.selector.models.counter import Counter
from analysis.selector.models.filter import Constraints, Filter
from analysis.selector.models.survey import Survey
from analysis.selector.models.track import Track
from analysis.selector.models.window import Window
from utils.mars import seasons as mars


def search(track: Track, criteria: Filter) -> Survey | None:
    """Search a timeline for the season the ground is best studied over.

    Args:
        track: The admissible observations on one time axis.
        criteria: The filter read against the feature, holding what it is asked.

    Returns:
        The chosen season, or None when no season is worth keeping.
    """
    # What the filter asks of this feature, worked out once when it was read
    windowed, standing = criteria.windowed, criteria.standing
    # What time cannot change is asked of the whole record rather than a season
    if standing:
        whole = Counter.over(track, 0, len(track.observations) - 1)
        if coverage_constraints(standing, whole.cells_reached) is None:
            return None
    # Take the best season
    picked = _best(track, windowed)
    if picked is None:
        return None
    # Clean up the record to only what is worth keeping, and report reached
    kept, reached = redundancy.trimmed(track, picked, windowed, configs.GAIN)
    year, season = mars.named(track.seasons[picked.first])
    return Survey(
        area_km2=track.grid.area_km2,
        start=track.observations[kept[0]].t_start,
        end=track.observations[kept[-1]].t_start,
        days=track.times[kept[-1]] - track.times[kept[0]],
        mars_year=year,
        season=season,
        geo_mean=_scored(track, reached),
        kept=tuple(kept),
        standing=timeless.fresh_looks(track, criteria.timeless),
    )


def _best(track: Track, windowed: Constraints) -> Window | None:
    """Take the season the feature is covered over the best.

    Args:
        track: The admissible observations on one time axis.
        windowed: The cells each instrument insisted on has to reach.

    Returns:
        The season covered the best, or None when none holds what is asked.
    """
    best: Window | None = None
    worth = float("-inf")
    tightest = float("inf")
    for season in seasons.cut(track):
        counter = Counter.over(track, season.first, season.last)
        counts = coverage_constraints(windowed, counter.cells_reached)
        if counts is None:
            continue  # the season does not hold what the filter asks
        reached = _scored(track, counts)
        # How much of the season its own looks are spread over, in longitude
        arc = track.ls[season.last] - track.ls[season.first]
        # The best covered season wins, and the closest gathered of any that tie
        if (reached, -arc) > (worth, -tightest):
            best, worth, tightest = season, reached, arc
    return best


def _scored(track: Track, counts: Sequence[int]) -> float:
    """Score what a season reaches of the feature.

    Args:
        track: The observations on one time axis.
        counts: The cells each constraint reaches, one count per constraint.

    Returns:
        The constraints rooted together as a share of the feature.
    """
    rooted = math.prod(counts) ** (1.0 / len(counts))
    return ground.share(rooted, track.grid.cell_km2, track.grid.area_km2)

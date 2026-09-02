"""Scoring a window on the ground it reaches, once its days are priced against it."""

from __future__ import annotations

import math
from collections.abc import Sequence

from analysis.selector import configs
from analysis.selector.models.track import Track
from analysis.utils.maths import ground

_PRICE_PER_DAY = 0.01 / configs.DAYS_PER_PERCENT


def scored(track: Track, counts: Sequence[int], days: float = 0.0) -> float:
    """Score what a window reaches, less what the days it runs for cost it.

    Args:
        track: The observations on one time axis.
        counts: The cells each constraint reaches, one count per constraint.
        days: How long the window runs, charged against the ground it reaches.

    Returns:
        The constraints rooted together as a share of the tile, less their days.
    """
    rooted = math.prod(counts) ** (1.0 / len(counts))
    geo_mean = ground.share(rooted, track.cell_km2, track.area_km2)
    return geo_mean - _PRICE_PER_DAY * days

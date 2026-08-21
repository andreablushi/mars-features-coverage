"""Which observations are a look at the feature rather than a clip of its edge."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import Event
from survey import configs


def admissible(observation: Event, cells: Sequence[int], width_km: float) -> bool:
    """Report whether one observation says enough about a feature to be counted.

    Args:
        observation: The observation, carrying the ground it landed in the feature.
        cells: The feature's cells its footprint fills.
        width_km: How wide the feature is, which only a sounder is measured
            against.

    Returns:
        True when the observation clears every floor asked of it.
    """
    # If it doesn't fill enough cells
    if len(cells) < configs.MIN_CELLS:
        return False
    # Under a minimum area
    if observation.own_km2 < configs.MIN_AREA_KM2:
        return False
    # Only SHARAD has a swath width, otherwise we are satisfied by this check
    if not observation.width_km:
        return True
    # The SHARAD line and not the width as to cross the feature
    crossed = observation.own_km2 / observation.width_km
    return crossed >= configs.MIN_CROSSING * width_km

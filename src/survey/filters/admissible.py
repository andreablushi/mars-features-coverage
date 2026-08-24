"""Which observations are a look at the feature rather than a clip of its edge."""

from __future__ import annotations

from models.results import Event
from survey import configs


def admissible(observation: Event, ground_km2: float, width_km: float) -> bool:
    """Report whether one observation says enough about a feature to be counted.

    Args:
        observation: The observation, which carries its swath width when it is
            a sounder track.
        ground_km2: The ground it lands inside the feature.
        width_km: How wide the feature is, which only a sounder is measured
            against.

    Returns:
        True when the observation clears every floor asked of it.
    """
    # Under a minimum area
    if ground_km2 < configs.MIN_AREA_KM2:
        return False
    # Only SHARAD has a swath width, otherwise we are satisfied by this check
    if not observation.width_km:
        return True
    # The SHARAD line and not the width as to cross the feature
    crossed = ground_km2 / observation.width_km
    return crossed >= configs.MIN_CROSSING * width_km

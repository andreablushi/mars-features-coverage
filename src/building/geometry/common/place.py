"""Turning the coordinates an instrument publishes into offsets from a feature."""

from __future__ import annotations

import numpy as np

from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from utils.geometry import geodesy


def offsets(
    latitude: np.ndarray,
    longitude: np.ndarray,
    frame: FeatureFrame,
    *,
    separable: bool,
) -> Placement:
    """Return where samples at those coordinates sit on one feature.

    Args:
        latitude: The latitude of every sample, or of every line where the grid
            is separable.
        longitude: The longitude of every sample, or of every sample of a line.
        frame: The local frame of the feature they were kept for.
        separable: Whether the two hold one axis each rather than a value for
            every sample.

    Returns:
        The placement, in degrees from the feature's own centre.
    """
    return Placement(
        north=latitude - frame.centre_lat,
        east=geodesy.normalise_longitude(longitude - frame.centre_lon),
        separable=separable,
    )

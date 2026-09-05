"""Turning the coordinates a sample carries into offsets from its feature."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from building.metadata.models.feature import FeatureFrame
from building.preprocessing.common.models.placement import Placement
from utils.geometry import geodesy


class Placed(Protocol):
    """What every instrument's sample says about where its own samples sit.

    Each instrument publishes its geometry differently, so a sample reads its
    own coordinates out of whatever its archive gave it. Saying them the same
    way is what lets one placement serve every instrument.

    Attributes:
        latitude: The latitude of every sample, or of every line where the grid
            is separable.
        longitude: The longitude of every sample, or of every sample of a line.
        separable: Whether those two hold one axis each rather than a value for
            every sample.
    """

    latitude: np.ndarray
    longitude: np.ndarray
    separable: bool


def place(sample: Placed, frame: FeatureFrame) -> Placement:
    """Return where every sample of one observation sits on its feature.

    Args:
        sample: The observation as it was read off disk, saying where its own
            samples were measured.
        frame: The local frame of the feature it was kept for.

    Returns:
        The placement, in degrees from that feature's own centre.
    """
    return Placement(
        north=sample.latitude - frame.centre_lat,
        east=geodesy.normalise_longitude(sample.longitude - frame.centre_lon),
        separable=sample.separable,
    )

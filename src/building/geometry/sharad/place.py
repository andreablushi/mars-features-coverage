"""Placing one SHARAD track on the feature it was kept for."""

from __future__ import annotations

from building.configs import sharad as configs
from building.geometry.common.models.placement import Placement
from building.geometry.common.place import offsets
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.sharad.models.sample import SharadSample


def place(sample: SharadSample, frame: FeatureFrame) -> Placement:
    """Return where every trace of one track sits on its feature.

    A sounder walks a line rather than sweeping ground, so its one ground axis
    is the track and each trace carries the pair its geometry sounded it at.

    Args:
        sample: The radargram holding only the traces its geometry places.
        frame: The local frame of the feature it was kept for.

    Returns:
        The placement, a pair per trace.
    """
    return offsets(
        sample.geometry[configs.PLACEMENT["latitude"]],
        sample.geometry[configs.PLACEMENT["longitude"]],
        frame,
        separable=False,
    )

"""Placing one CTX scan on the feature it was kept for."""

from __future__ import annotations

from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.ctx.models.sample import CtxSample
from utils.geometry import geodesy


def place(sample: CtxSample, frame: FeatureFrame) -> Placement:
    """Return where every pixel of one scan sits on its feature.

    A CTX RDR is projected onto a regular grid, so a line's latitude and a
    sample's longitude place it between them and no pixel needs its own pair.

    Args:
        sample: The scan as it was read off disk.
        frame: The local frame of the feature it was kept for.

    Returns:
        The placement, one axis each.
    """
    return Placement(
        north=sample.latitude - frame.centre_lat,
        east=geodesy.normalise_longitude(sample.longitude - frame.centre_lon),
        separable=True,
    )

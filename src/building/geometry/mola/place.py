"""Placing one MOLA tile on the feature it was kept for."""

from __future__ import annotations

from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.mola.models.sample import MolaSample
from utils.geometry import geodesy


def place(sample: MolaSample, frame: FeatureFrame) -> Placement:
    """Return where every bin of one tile sits on its feature.

    A gridded tile is simple cylindrical, so a line's latitude and a sample's
    longitude place it between them and no bin needs its own pair.

    Args:
        sample: The tile as it was read off disk.
        frame: The local frame of the feature it was kept for.

    Returns:
        The placement, one axis each.
    """
    return Placement(
        north=sample.latitude - frame.centre_lat,
        east=geodesy.normalise_longitude(sample.longitude - frame.centre_lon),
        separable=True,
    )

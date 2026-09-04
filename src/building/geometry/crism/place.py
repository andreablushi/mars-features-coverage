"""Placing one CRISM observation on the feature it was kept for."""

from __future__ import annotations

from building.configs import crism as configs
from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.crism.models.sample import CrismSample
from utils.geometry import geodesy


def place(sample: CrismSample, frame: FeatureFrame) -> Placement:
    """Return where every pixel of one observation sits on its feature.

    A pushbroom swath bends as the spacecraft flies, so its grid is not two
    axes crossed and every pixel carries the pair its backplanes give it.

    Args:
        sample: The observation with its two detectors joined.
        frame: The local frame of the feature it was kept for.

    Returns:
        The placement, a pair per pixel.
    """
    return Placement(
        north=sample.geometry[:, :, configs.BACKPLANES["latitude"]] - frame.centre_lat,
        east=geodesy.normalise_longitude(
            sample.geometry[:, :, configs.BACKPLANES["longitude"]] - frame.centre_lon
        ),
        separable=False,
    )

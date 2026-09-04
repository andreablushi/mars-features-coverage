"""Cutting one SHARAD track down to the ground its feature covers."""

from __future__ import annotations

from building.crop.common.cut import cut, cut_placement, feature_box
from building.crop.common.models.crop import Crop
from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.sharad.models.sample import SharadSample


def crop(
    sample: SharadSample, placement: Placement, frame: FeatureFrame
) -> Crop[SharadSample] | None:
    """Return one track cut to the box of the feature it was kept for.

    A sounder walks a line rather than sweeping ground, so only the traces are
    cut and the delay each one was sounded over is left whole.

    Args:
        sample: The radargram holding only the traces its geometry places.
        placement: Where those traces sit, against the same feature.
        frame: The local frame of the feature it was kept for.

    Returns:
        The crop, or None where the track reaches none of the feature.
    """
    held = cut(placement, feature_box(frame))
    if held is None:
        return None
    (traces,) = held.bounds
    return Crop(
        sample=SharadSample(
            identifier=sample.identifier,
            power=sample.power[:, traces],
            geometry=sample.geometry[traces],
            traces=sample.traces[traces],
        ),
        placement=cut_placement(placement, held),
        inside=held.inside,
    )

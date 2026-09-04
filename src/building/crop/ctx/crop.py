"""Cutting one CTX scan down to the ground its feature covers."""

from __future__ import annotations

from building.crop.common.cut import cut, cut_placement, taken
from building.crop.common.models.crop import Crop
from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.ctx.models.sample import CtxSample


def crop(
    sample: CtxSample, placement: Placement, frame: FeatureFrame
) -> Crop[CtxSample] | None:
    """Return one scan cut to the box of the feature it was kept for.

    A scan is projected onto a grid the box is a rectangle on, so the cut is a
    range of lines and a range of samples and every pixel it keeps is inside.

    Args:
        sample: The scan as it was read off disk.
        placement: Where its pixels sit, against the same feature.
        frame: The local frame of the feature it was kept for.

    Returns:
        The crop, or None where the scan reaches none of the feature.
    """
    held = cut(placement, frame)
    if held is None:
        return None
    lines, samples = held.bounds
    return Crop(
        sample=CtxSample(
            identifier=sample.identifier,
            image=taken(sample.image, held.bounds),
            latitude=sample.latitude[lines],
            longitude=sample.longitude[samples],
            pixel=sample.pixel,
        ),
        placement=cut_placement(placement, held),
        inside=held.inside,
    )

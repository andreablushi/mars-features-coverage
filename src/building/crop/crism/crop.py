"""Cutting one CRISM observation down to the ground its feature covers."""

from __future__ import annotations

from building.crop.common.cut import cut, cut_placement, feature_box, taken
from building.crop.common.models.crop import Crop
from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.crism.models.sample import CrismSample


def crop(
    sample: CrismSample, placement: Placement, frame: FeatureFrame
) -> Crop[CrismSample] | None:
    """Return one observation cut to the box of the feature it was kept for.

    A swath bends as the spacecraft flies, so the box is no rectangle on it and
    the corners of the cut can fall outside the feature. Those are marked
    rather than dropped, so what is left is still an image.

    Args:
        sample: The observation with its two detectors joined.
        placement: Where its pixels sit, against the same feature.
        frame: The local frame of the feature it was kept for.

    Returns:
        The crop, or None where the observation reaches none of the feature.
    """
    held = cut(placement, feature_box(frame))
    if held is None:
        return None
    columns = held.bounds[1]
    return Crop(
        sample=CrismSample(
            identifier=sample.identifier,
            cube=taken(sample.cube, held.bounds),
            wavelengths=sample.wavelengths[columns],
            geometry=taken(sample.geometry, held.bounds),
            columns=sample.columns[columns],
        ),
        placement=cut_placement(placement, held),
        inside=held.inside,
    )

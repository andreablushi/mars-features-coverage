"""Cutting one MOLA tile down to the ground its feature covers."""

from __future__ import annotations

from building.crop.common.cut import cut, cut_placement, feature_box, taken
from building.crop.common.models.crop import Crop
from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.mola.models.sample import MolaSample


def crop(
    sample: MolaSample, placement: Placement, frame: FeatureFrame
) -> Crop[MolaSample] | None:
    """Return one tile cut to the box of the feature it was kept for.

    A gridded tile is simple cylindrical, so the box is a rectangle on it and
    the cut is a range of lines and a range of samples of both planes at once.

    Args:
        sample: The tile as it was read off disk.
        placement: Where its bins sit, against the same feature.
        frame: The local frame of the feature it was kept for.

    Returns:
        The crop, or None where the tile reaches none of the feature.
    """
    held = cut(placement, feature_box(frame))
    if held is None:
        return None
    lines, samples = held.bounds
    return Crop(
        sample=MolaSample(
            identifier=sample.identifier,
            topography=taken(sample.topography, held.bounds),
            counts=taken(sample.counts, held.bounds),
            latitude=sample.latitude[lines],
            longitude=sample.longitude[samples],
            resolution=sample.resolution,
        ),
        placement=cut_placement(placement, held),
        inside=held.inside,
    )

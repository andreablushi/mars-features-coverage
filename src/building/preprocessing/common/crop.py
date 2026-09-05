"""Cutting one placed observation down to the ground its own feature covers."""

from __future__ import annotations

from typing import Protocol, Self

from building.metadata.models.feature import FeatureFrame
from building.preprocessing.common.cut import cut, cut_placement
from building.preprocessing.common.models.crop import Crop
from building.preprocessing.common.models.cut import Cut
from building.preprocessing.common.models.placement import Placement


class Cuttable(Protocol):
    """What every instrument's sample can do when a feature keeps part of it."""

    def cut(self, held: Cut) -> Self:
        """Return this sample holding only the samples one cut keeps.

        Each instrument publishes its arrays in its own shape, and which axis of
        one is ground differs between them, so a sample cuts itself rather than
        being cut by a rule imposed from outside.

        Args:
            held: What the feature's box keeps of it.

        Returns:
            The sample, every array of it cut the way that array is laid out.
        """
        ...


def crop[Sample: Cuttable](
    sample: Sample, placement: Placement, frame: FeatureFrame
) -> Crop[Sample] | None:
    """Return one observation cut to the box of the feature it was kept for.

    Args:
        sample: The observation as it was read off disk.
        placement: Where its samples sit, against that same feature.
        frame: The local frame of the feature it was kept for.

    Returns:
        The crop, or None where the observation reaches none of the feature.
    """
    held = cut(placement, frame)
    if held is None:
        return None
    return Crop(
        sample=sample.cut(held),
        placement=cut_placement(placement, held),
        inside=held.inside,
    )

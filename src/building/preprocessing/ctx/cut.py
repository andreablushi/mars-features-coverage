"""Cutting one CTX scan's arrays down to what its feature's box keeps."""

from __future__ import annotations

from building.preprocessing.common.cut import taken
from building.preprocessing.common.models.cut import Cut
from building.preprocessing.ctx.models.sample import CtxSample


def cut(sample: CtxSample, held: Cut) -> CtxSample:
    """Return one scan holding only the pixels a cut keeps.

    A scan is projected onto a grid the box is a rectangle on, so the cut is a
    range of lines and a range of samples, and one axis is cut by each.

    Args:
        sample: The scan as it was read off disk.
        held: What the feature's box keeps of it.

    Returns:
        The scan cut to it, the degrees one pixel spans unchanged.
    """
    lines, samples = held.bounds
    return CtxSample(
        identifier=sample.identifier,
        image=taken(sample.image, held.bounds),
        latitude=sample.latitude[lines],
        longitude=sample.longitude[samples],
        pixel=sample.pixel,
    )

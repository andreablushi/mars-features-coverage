"""Reading one CTX observation off disk, whole."""

from __future__ import annotations

from preprocessing.ctx.loaders import geometry, image
from preprocessing.ctx.loaders.utils import locations
from preprocessing.ctx.models.observation import CtxObservation
from preprocessing.pds import labels


def read(identifier: str) -> CtxObservation:
    """Read the scan and the label one observation was published as.

    Args:
        identifier: The observation, whose files must already be in the cache
            that `download.fetch` puts them in.

    Returns:
        The observation, its image loaded and placed on the grid its label
        projects it onto.

    Raises:
        FileNotFoundError: When the image or its label is missing.
        ValueError: When the label names a projection this cannot read, or the
            image holds more than one plane.
    """
    label = labels.load(locations.label(identifier))
    return CtxObservation(
        identifier, image.load(identifier), label, *geometry.load(label)
    )

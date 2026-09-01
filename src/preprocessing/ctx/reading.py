"""Reading one CTX observation off disk, whole."""

from __future__ import annotations

import tifffile

from preprocessing.common.pds import labels
from preprocessing.ctx import geometry, locations
from preprocessing.ctx.models.observation import CtxObservation


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
    # ASU publishes the pixels as a TIFF rather than beside a label of their own.
    image = tifffile.imread(locations.image(identifier))
    if image.ndim != 2:
        raise ValueError(f"{identifier} holds a {image.ndim} dimensional image.")
    return CtxObservation(identifier, image, label, *geometry.load(label))

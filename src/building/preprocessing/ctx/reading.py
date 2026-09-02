"""Reading one CTX observation off disk, whole."""

from __future__ import annotations

import tifffile

from building.preprocessing.common.pds import labels
from building.preprocessing.ctx import configs
from building.preprocessing.ctx.models.observation import CtxObservation
from building.preprocessing.ctx.utils import geometry


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
    files = configs.CACHE.files(identifier, identifier)
    label = labels.load(files[configs.SUFFIXES[configs.LABEL]])
    # ASU publishes the pixels as a TIFF rather than beside a label of their own.
    image = tifffile.imread(files[configs.SUFFIXES[configs.IMAGE]])
    if image.ndim != 2:
        raise ValueError(f"{identifier} holds a {image.ndim} dimensional image.")
    return CtxObservation(identifier, image, label, *geometry.load(label))

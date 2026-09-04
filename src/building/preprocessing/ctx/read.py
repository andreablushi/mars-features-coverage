"""Reading one CTX observation off disk and placing it on its grid."""

from __future__ import annotations

import tifffile

from building.common.pds import labels
from building.configs import ctx as configs
from building.preprocessing.ctx import geometry
from building.preprocessing.ctx.models.sample import CtxSample

# What the projection writes where the scan swept no ground.
BLANK = 0


def read(identifier: str) -> CtxSample:
    """Read one scan and place it on the grid its label projects it onto.

    Args:
        identifier: The observation, whose files must already be in the cache
            that `download.fetch` puts them in.

    Returns:
        The sample, its image on that grid and the pixels it never measured
        marked.

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
    latitude, longitude = geometry.load(label)
    return CtxSample(
        identifier, image, image == BLANK, latitude, longitude, geometry.pixel(label)
    )

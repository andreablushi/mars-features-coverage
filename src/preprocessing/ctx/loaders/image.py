"""Loading the projected scan one CTX observation was published as."""

from __future__ import annotations

import numpy as np
import tifffile

from preprocessing.ctx.loaders.utils import locations


def load(observation_id: str) -> np.ndarray:
    """Read one scan's projected image off disk.

    Args:
        observation_id: The observation, whose files must already be in the
            cache that `download.fetch` puts them in.

    Returns:
        The brightness as lines by samples, as ASU stretched it, with zero
        standing for the ground the projection left blank.

    Raises:
        FileNotFoundError: When the image is missing.
        ValueError: When the file holds more than one plane.
    """
    image = locations.image(observation_id)
    values = tifffile.imread(image)
    if values.ndim != 2:
        raise ValueError(f"{image.name} holds a {values.ndim} dimensional image.")
    return values

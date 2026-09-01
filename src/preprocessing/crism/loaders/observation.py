"""Loading the scan one detector of an observation was published as."""

from __future__ import annotations

import numpy as np

from preprocessing.crism.loaders.utils import locations, naming
from preprocessing.pds import images, labels


def load(observation_id: str, detector: str) -> tuple[np.ndarray, dict[str, str]]:
    """Read one detector's scan off disk.

    Args:
        observation_id: The observation, whose files must already be in the
            cache that `download.fetch` puts them in.
        detector: Which detector, `l` for infrared or `s` for visible.

    Returns:
        The I/F values as lines by samples by bands, in the band order the file
        stores them in, and the parsed label describing them.

    Raises:
        FileNotFoundError: When the image or its label is missing.
        ValueError: When the label names a band order this cannot read.
    """
    image = locations.files(observation_id, detector, naming.OBSERVATION)[".img"]
    label = labels.load(image.with_suffix(".lbl"))
    return images.build_cube(image, label), label

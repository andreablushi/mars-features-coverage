"""Loading the radargram one SHARAD track was published as."""

from __future__ import annotations

import numpy as np

from preprocessing.pds import images, labels
from preprocessing.sharad.loaders.utils import locations, naming


def load(observation_id: str) -> tuple[np.ndarray, dict[str, str]]:
    """Read one track's radargram off disk.

    Args:
        observation_id: The observation, whose files must already be in the
            cache that `download.fetch` puts them in.

    Returns:
        The backscatter power as delay samples by traces, and the parsed label
        describing it.

    Raises:
        FileNotFoundError: When the image or its label is missing.
        KeyError: When the label names a sample type this cannot read.
    """
    image = locations.files(observation_id, naming.OBSERVATION)[".img"]
    label = labels.load(image.with_suffix(".lbl"))
    # A radargram carries one value per pixel, so drop the band a cube keeps.
    return images.build_cube(image, label)[:, :, 0], label

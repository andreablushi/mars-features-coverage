"""Loading the geometry published beside one detector of an observation."""

from __future__ import annotations

import numpy as np

from preprocessing.crism.loaders.utils import locations, naming, pds


def load(observation_id: str, detector: str) -> tuple[np.ndarray, dict[str, str]]:
    """Read one detector's geometry off disk.

    Args:
        observation_id: The observation, whose files must already be in the
            cache that `download.fetch` puts them in.
        detector: Which detector, `l` for infrared or `s` for visible.

    Returns:
        The backplanes as lines by samples by 14, on the same grid as the scan,
        and the parsed label whose BAND_NAME says what each one holds.

    Raises:
        FileNotFoundError: When the image or its label is missing.
        ValueError: When the label names a band order this cannot read.
    """
    image = locations.files(observation_id, detector, naming.GEOMETRY)[".img"]
    label = pds.load_label(image.with_suffix(".lbl"))
    return pds.build_cube(image, label), label

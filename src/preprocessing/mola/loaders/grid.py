"""Loading one plane of a MOLA tile."""

from __future__ import annotations

import numpy as np

from preprocessing.mola.loaders.utils import locations, naming
from preprocessing.pds import images, labels


def load(tile: str, kind: str = naming.TOPOGRAPHY) -> tuple[np.ndarray, dict[str, str]]:
    """Read one plane of a tile off disk.

    Args:
        tile: The tile, whose files must already be in the cache that
            `download.fetch` puts them in.
        kind: Which plane, `naming.TOPOGRAPHY` or `naming.COUNTS`.

    Returns:
        The values as lines by samples, in the type the archive stores them in,
        which is metres for topography and shots per bin for counts, and the
        parsed label describing them.

    Raises:
        FileNotFoundError: When the image or its label is missing.
        KeyError: When the label names a sample type this cannot read.
    """
    image = locations.files(tile, kind)[".img"]
    label = labels.load(image.with_suffix(".lbl"))
    # A gridded plane carries one value per pixel, so drop the band a cube keeps.
    return images.build_cube(image, label)[:, :, 0], label

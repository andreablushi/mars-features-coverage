"""What one cropped MOLA tile contributes to the dataset."""

from __future__ import annotations

from pathlib import Path

import utils.disk.paths as paths
from building.configs import mola as configs
from building.crop.common.models.crop import Crop
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.mola.models.sample import MolaSample
from building.writing.common import store

# Which of the arrays written is the measurement itself.
MEASUREMENT = "topography"

GROUND = store.ground_dims(configs.DIMS, configs.AXES)


def write(
    held: Crop[MolaSample], frame: FeatureFrame, root: Path = paths.DATASET_ROOT
) -> Path:
    """Write one cropped tile down, its height and how each bin was measured.

    Args:
        held: The tile cut to the feature it was kept for.
        frame: That feature's local frame.
        root: The dataset's own root directory.

    Returns:
        The directory the crop was written in.
    """
    return store.write_crop(
        held,
        {
            MEASUREMENT: (held.sample.topography, configs.DIMS),
            "counts": (held.sample.counts, configs.DIMS),
        },
        MEASUREMENT,
        GROUND,
        frame,
        "MOLA",
        held.sample.identifier,
        root,
    )

"""What one cropped CTX scan contributes to the dataset."""

from __future__ import annotations

from pathlib import Path

import utils.disk.paths as paths
from building.configs import ctx as configs
from building.crop.common.models.crop import Crop
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.ctx.models.sample import CtxSample
from building.writing.common import store

# Which of the arrays written is the measurement itself.
MEASUREMENT = "image"

GROUND = store.ground_dims(configs.DIMS, configs.AXES)


def write(
    held: Crop[CtxSample], frame: FeatureFrame, root: Path = paths.DATASET_ROOT
) -> Path:
    """Write one cropped scan down, its brightness and the ground it swept.

    Args:
        held: The scan cut to the feature it was kept for.
        frame: That feature's local frame.
        root: The dataset's own root directory.

    Returns:
        The directory the crop was written in.
    """
    return store.write_crop(
        held,
        {
            MEASUREMENT: (held.sample.image, configs.DIMS),
            "blank": (held.sample.blank, configs.DIMS),
        },
        MEASUREMENT,
        GROUND,
        frame,
        "CTX",
        held.sample.identifier,
        root,
    )

"""What one cropped CTX scan contributes to the dataset."""

from __future__ import annotations

from pathlib import Path

import utils.disk.paths as paths
from building.configs import ctx as configs
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.common.models.crop import Crop
from building.preprocessing.ctx.models.sample import CtxSample
from building.writing.common import store


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
            configs.LAYOUT.measurement: (held.sample.image, configs.LAYOUT.dims),
            "blank": (held.sample.blank, configs.LAYOUT.dims),
        },
        configs.LAYOUT,
        frame,
        root,
    )

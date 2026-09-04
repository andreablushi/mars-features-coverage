"""What one cropped SHARAD track contributes to the dataset."""

from __future__ import annotations

from pathlib import Path

import utils.disk.paths as paths
from building.configs import sharad as configs
from building.crop.common.models.crop import Crop
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.sharad.models.sample import SharadSample
from building.writing.common import store


def write(
    held: Crop[SharadSample], frame: FeatureFrame, root: Path = paths.DATASET_ROOT
) -> Path:
    """Write one cropped track down, its echoes and which columns they were.

    Args:
        held: The track cut to the feature it was kept for.
        frame: That feature's local frame.
        root: The dataset's own root directory.

    Returns:
        The directory the crop was written in.
    """
    (trace,) = configs.LAYOUT.ground
    return store.write_crop(
        held,
        {
            configs.LAYOUT.measurement: (held.sample.power, configs.LAYOUT.dims),
            "traces": (held.sample.traces, (trace,)),
        },
        configs.LAYOUT,
        frame,
        root,
    )

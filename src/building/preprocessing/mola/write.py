"""What one cropped MOLA tile contributes to the dataset."""

from __future__ import annotations

from pathlib import Path

import utils.disk.paths as paths
from building.configs import mola as configs
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.common import store
from building.preprocessing.common.models.crop import Crop
from building.preprocessing.mola.models.sample import MolaSample


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
            configs.LAYOUT.measurement: (held.sample.topography, configs.LAYOUT.dims),
            "counts": (held.sample.counts, configs.LAYOUT.dims),
        },
        configs.LAYOUT,
        frame,
        root,
    )

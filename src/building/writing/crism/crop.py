"""What one cropped CRISM observation contributes to the dataset."""

from __future__ import annotations

from pathlib import Path

import utils.disk.paths as paths
from building.configs import crism as configs
from building.crop.common.models.crop import Crop
from building.metadata.models.feature import FeatureFrame
from building.preprocessing.crism.models.sample import CrismSample
from building.writing.common import store

# Which of the arrays written is the measurement itself.
MEASUREMENT = "cube"

GROUND = store.ground_dims(configs.DIMS, configs.AXES)


def write(
    held: Crop[CrismSample], frame: FeatureFrame, root: Path = paths.DATASET_ROOT
) -> Path:
    """Write one cropped observation down, its cube and what each band holds.

    The detector is calibrated column by column, so a wavelength is written
    against the column it was measured on rather than against the band alone.

    Args:
        held: The observation cut to the feature it was kept for.
        frame: That feature's local frame.
        root: The dataset's own root directory.

    Returns:
        The directory the crop was written in.
    """
    _, sample, band = configs.DIMS
    return store.write_crop(
        held,
        {
            MEASUREMENT: (held.sample.cube, configs.DIMS),
            "wavelengths": (held.sample.wavelengths, (sample, band)),
            "columns": (held.sample.columns, (sample,)),
        },
        MEASUREMENT,
        GROUND,
        frame,
        "CRISM",
        held.sample.identifier,
        root,
    )

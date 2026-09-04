"""Reading the written dataset back, which is how another repository holds it."""

from __future__ import annotations

from pathlib import Path

import utils.disk.paths as paths
from building.metadata import read as metadata
from building.writing.models.dataset import Dataset


def read_dataset(root: Path = paths.DATASET_ROOT) -> Dataset:
    """Read every crop the dataset holds, without opening one of them.

    The index alone is read, so a split or a count costs nothing and only a
    crop that is asked for is ever loaded off disk.

    Args:
        root: The dataset's own directory.

    Returns:
        The dataset, its frames and its records.

    Raises:
        FileNotFoundError: When no dataset has been written there.
    """
    return Dataset(
        root=root,
        frames=metadata.read_feature_frames(root),
        records=tuple(metadata.read_observation_records(root)),
    )

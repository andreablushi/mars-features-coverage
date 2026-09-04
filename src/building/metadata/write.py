"""Writing the metadata down: where each feature is, and what was taken of it."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import utils.disk.paths as paths
from building.metadata.models.feature import FeatureFrame
from building.metadata.models.observation import ObservationRecord
from utils.disk import parquet

FRAMES = parquet.schema_of(FeatureFrame)
RECORDS = parquet.schema_of(ObservationRecord)


def write_metadata(
    frames: Sequence[FeatureFrame],
    records: Sequence[ObservationRecord],
    root: Path = paths.DATASET_ROOT,
) -> tuple[Path, Path]:
    """Write every feature's frame down, and every observation taken of them.

    Args:
        frames: One frame per feature, in the order to write them.
        records: One record per feature and observation, in the same manner.
        root: The directory the two files are written in, made when missing.

    Returns:
        The frames file and the records file, in that order.
    """
    root.mkdir(parents=True, exist_ok=True)
    frames_path = root / paths.FEATURE_FRAMES_NAME
    records_path = root / paths.OBSERVATION_RECORDS_NAME
    parquet.write(frames, FRAMES, frames_path)
    parquet.write(records, RECORDS, records_path)
    return frames_path, records_path

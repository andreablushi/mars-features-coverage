"""Reading the written metadata back, which every stored array is read through."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

import utils.disk.paths as paths
from building.metadata.models.feature import FeatureFrame
from building.metadata.models.observation import ObservationRecord
from building.metadata.write import FRAMES, RECORDS


def read_feature_frames(
    root: Path = paths.FRAMES_ROOT,
) -> dict[tuple[str, str], FeatureFrame]:
    """Read the local frame of every feature, keyed by the feature it belongs to.

    Args:
        root: The directory the metadata was written in.

    Returns:
        Each feature's frame, by class and name.

    Raises:
        FileNotFoundError: When no frames have been written there.
    """
    path = root / paths.FEATURE_FRAMES_NAME
    if not path.is_file():
        raise FileNotFoundError(f"no feature frames were written in {root}")
    return {
        (frame.feature_class, frame.feature_name): frame
        for frame in (
            FeatureFrame(**row)
            for row in pq.read_table(path, schema=FRAMES).to_pylist()
        )
    }


def read_observation_records(
    root: Path = paths.FRAMES_ROOT,
) -> list[ObservationRecord]:
    """Read what every stored observation is, in the order they were written.

    Args:
        root: The directory the metadata was written in.

    Returns:
        One record per feature and observation.

    Raises:
        FileNotFoundError: When no records have been written there.
    """
    path = root / paths.OBSERVATION_RECORDS_NAME
    if not path.is_file():
        raise FileNotFoundError(f"no observation records were written in {root}")
    return [
        ObservationRecord(
            **{**row, "axes": tuple(row["axes"]), "shape": tuple(row["shape"])}
        )
        for row in pq.read_table(path, schema=RECORDS).to_pylist()
    ]

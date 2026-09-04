"""Reading the written metadata back, which every stored array is read through."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import utils.disk.paths as paths
from building.metadata.models.feature import FeatureFrame
from building.metadata.models.observation import ObservationRecord
from building.metadata.write import FRAMES, RECORDS


def read_feature_frames(
    root: Path = paths.DATASET_ROOT,
) -> dict[tuple[str, str], FeatureFrame]:
    """Read the local frame of every feature, keyed by the feature it belongs to.

    Args:
        root: The directory the metadata was written in.

    Returns:
        Each feature's frame, by class and name.

    Raises:
        FileNotFoundError: When no frames have been written there.
    """
    held = _rows(
        root / paths.FEATURE_FRAMES_NAME,
        FRAMES,
        FeatureFrame,
        f"no feature frames were written in {root}",
    )
    return {(frame.feature_class, frame.feature_name): frame for frame in held}


def read_observation_records(
    root: Path = paths.DATASET_ROOT,
) -> list[ObservationRecord]:
    """Read what every stored observation is, in the order they were written.

    Args:
        root: The directory the metadata was written in.

    Returns:
        One record per feature and observation.

    Raises:
        FileNotFoundError: When no records have been written there.
    """
    return _rows(
        root / paths.OBSERVATION_RECORDS_NAME,
        RECORDS,
        ObservationRecord,
        f"no observation records were written in {root}",
    )


def _rows[Row](
    path: Path, schema: pa.Schema, model: type[Row], missing: str
) -> list[Row]:
    """Read one written file back into the rows it holds.

    Args:
        path: The file to read.
        schema: The schema it was written under.
        model: The row model to read each row into.
        missing: What to say where nothing has been written.

    Returns:
        One row model per row, in the order they were written.

    Raises:
        FileNotFoundError: When nothing has been written there.
    """
    if not path.is_file():
        raise FileNotFoundError(missing)
    # A field the model holds as a tuple is written as a list, so it is read
    # back as the tuple it was and not as the list parquet hands over.
    listed = [field.name for field in schema if pa.types.is_list(field.type)]
    return [
        model(**{**row, **{name: tuple(row[name]) for name in listed}})
        for row in pq.read_table(path, schema=schema).to_pylist()
    ]

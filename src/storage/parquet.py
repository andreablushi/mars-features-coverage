"""Reading and writing the parquet artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

import configs
from models.results import Event, SetCoverage, Summary
from storage import layout
from storage.files import atomic_path
from storage.schemas import EVENTS, SUMMARY


def write(rows: Sequence[Any], schema: pa.Schema, path: Path) -> None:
    """Write dataclass rows to a parquet file.

    The rows are read column by column rather than turned into dictionaries,
    because arrow wants columns anyway and a row is only ever read once.

    Args:
        rows: The dataclass rows to write, whose fields match the schema.
        schema: The schema to write them under.
        path: The destination parquet file.

    Returns:
        None.
    """
    columns = {name: [getattr(row, name) for row in rows] for name in schema.names}
    write_columns(columns, schema, path)


def write_columns(
    columns: Mapping[str, Sequence[Any]], schema: pa.Schema, path: Path
) -> None:
    """Write columns to a parquet file, atomically.

    Args:
        columns: The columns to write, keyed by the schema's field names.
        schema: The schema to write them under.
        path: The destination parquet file.

    Returns:
        None.
    """
    table = pa.Table.from_pydict(dict(columns), schema=schema)
    with atomic_path(path) as tmp:
        pq.write_table(table, tmp, compression="zstd")


def computed_features(root: Path = configs.COVERAGE_ROOT) -> set[tuple[str, str]]:
    """Return every feature that has coverage computed locally.

    Args:
        root: The coverage artifacts root directory.

    Returns:
        The class and name slug of each feature holding at least one computed
        instrument set.
    """
    return {
        (path.parent.parent.name, path.parent.name)
        for path in root.glob(f"*/*/*{configs.EVENTS_SUFFIX}")
    }


def load_feature(
    feature_class: str, name: str, root: Path = configs.COVERAGE_ROOT
) -> list[SetCoverage]:
    """Read every computed instrument set for one feature.

    Args:
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.
        root: The coverage artifacts root directory.

    Returns:
        One entry per finished instrument set, widest coverage first. A run
        that kept no union measured no coverage to rank by, so those sets fall
        back to the busiest first.
    """
    directory = layout.feature_artifacts_dir(root, feature_class, name)
    loaded = [
        _load_set(path) for path in sorted(directory.glob(f"*{configs.EVENTS_SUFFIX}"))
    ]
    return sorted(
        (entry for entry in loaded if entry),
        key=lambda entry: (-(entry.summary.covered_frac or 0.0), -entry.summary.n_obs),
    )


def _load_set(events_path: Path) -> SetCoverage | None:
    """Read one instrument set's events and summary.

    Args:
        events_path: The set's events parquet file.

    Returns:
        The set's coverage, or None when its summary is missing, which marks a
        set whose computation never finished.
    """
    summary_path = events_path.with_name(
        events_path.name.replace(configs.EVENTS_SUFFIX, configs.SET_SUMMARY_SUFFIX)
    )
    if not summary_path.exists():
        return None
    summary = pq.read_table(summary_path, schema=SUMMARY).to_pylist()
    events = pq.read_table(events_path, schema=EVENTS).to_pylist()
    return SetCoverage(
        events=[Event(**row) for row in events], summary=Summary(**summary[0])
    )

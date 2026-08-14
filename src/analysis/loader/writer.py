"""Writing coverage results out as parquet and raw geometry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from common.files import atomic_path


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

"""Writing the parquet artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from utils.disk.files import atomic_path


def write(
    data: Mapping[str, Sequence[Any]] | Sequence[Any], schema: pa.Schema, path: Path
) -> None:
    """Write dataclass rows, or ready-made columns, to a parquet file atomically.

    Args:
        data: The dataclass rows to write, or the columns keyed by the schema's fields.
        schema: The schema to write them under.
        path: The destination parquet file.

    Returns:
        None.
    """
    columns = (
        data
        if isinstance(data, Mapping)
        else {name: [getattr(row, name) for row in data] for name in schema.names}
    )
    table = pa.Table.from_pydict(dict(columns), schema=schema)
    with atomic_path(path) as tmp:
        pq.write_table(table, tmp, compression="zstd")

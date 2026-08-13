"""Writing coverage results out as parquet."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from common.atomic import atomic_path


def write(rows: Sequence[Any], schema: pa.Schema, path: Path) -> None:
    """Write rows to a parquet file, atomically via a temp file and rename.

    Args:
        rows: The dataclass rows to write, whose fields match the schema.
        schema: The schema to write them under.
        path: The destination parquet file.

    Returns:
        None.
    """
    table = pa.Table.from_pylist([asdict(row) for row in rows], schema=schema)
    with atomic_path(path) as tmp:
        pq.write_table(table, tmp, compression="zstd")

"""Writing coverage results out as parquet."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from common.atomic import atomic_path


def write(rows: Sequence[dict[str, Any]], schema: pa.Schema, path: Path) -> None:
    """Write rows to a parquet file, atomically via a temp file and rename.

    Args:
        rows: The rows to write, each keyed by the schema's field names.
        schema: The schema to write them under.
        path: The destination parquet file.

    Returns:
        None.
    """
    table = pa.Table.from_pylist(list(rows), schema=schema)
    with atomic_path(path) as tmp:
        pq.write_table(table, tmp, compression="zstd")

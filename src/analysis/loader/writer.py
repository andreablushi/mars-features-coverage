"""Writing coverage results out as parquet and raw geometry."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from common.atomic import atomic_path


def write(rows: Sequence[Any], schema: pa.Schema, path: Path) -> None:
    """Write dataclass rows to a parquet file.

    Args:
        rows: The dataclass rows to write, whose fields match the schema.
        schema: The schema to write them under.
        path: The destination parquet file.

    Returns:
        None.
    """
    write_rows([asdict(row) for row in rows], schema, path)


def write_rows(rows: Sequence[dict[str, Any]], schema: pa.Schema, path: Path) -> None:
    """Write mapping rows to a parquet file, atomically.

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


def write_bytes(payload: bytes, path: Path) -> None:
    """Write raw bytes to a file, atomically.

    Args:
        payload: The bytes to write.
        path: The destination file.

    Returns:
        None.
    """
    with atomic_path(path) as tmp:
        tmp.write_bytes(payload)

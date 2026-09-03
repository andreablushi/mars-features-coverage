"""Writing the parquet artifacts, under a schema derived from the rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from types import NoneType, UnionType
from typing import Any, get_args, get_type_hints

import pyarrow as pa
import pyarrow.parquet as pq

from utils.disk.files import atomic_path

_ARROW = {
    str: pa.string(),
    int: pa.int64(),
    float: pa.float64(),
    bool: pa.bool_(),
    bytes: pa.binary(),
    datetime: pa.timestamp("us", tz="UTC"),
}


def schema_of(model: type) -> pa.Schema:
    """Derive the parquet schema a row model is written under.

    Args:
        model: The dataclass whose fields become the columns, in their own order.

    Returns:
        The schema, every column nullable as parquet writes them.
    """
    hints = get_type_hints(model)
    columns = []
    for field in fields(model):
        kind = hints[field.name]
        # A column a row may leave unset is written as the type it holds when set
        if isinstance(kind, UnionType):
            kind = next(one for one in get_args(kind) if one is not NoneType)
        columns.append((field.name, _ARROW[kind]))
    return pa.schema(columns)


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

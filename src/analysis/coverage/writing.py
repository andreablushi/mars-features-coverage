"""Writing one instrument set's coverage artifacts, under a derived schema."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import datetime
from types import NoneType, UnionType
from typing import get_args, get_type_hints

import pyarrow as pa

from analysis.coverage.models.coverage import Event
from analysis.coverage.models.summary import Summary
from analysis.models.job import Job
from analysis.utils import parquet

_ARROW = {
    str: pa.string(),
    int: pa.int64(),
    float: pa.float64(),
    bytes: pa.binary(),
    datetime: pa.timestamp("us", tz="UTC"),
}


def _schema(model: type) -> pa.Schema:
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


EVENTS = _schema(Event)
SUMMARY = _schema(Summary)


def write_coverage(job: Job, events: Sequence[Event], summary: Summary) -> None:
    """Write one set's observation rows and the single row describing it.

    Args:
        job: The instrument set that was computed, naming both destinations.
        events: The set's observation rows, in chronological order.
        summary: The one row describing the set as a whole.

    Returns:
        None.
    """
    parquet.write(events, EVENTS, job.events_path)
    parquet.write([summary], SUMMARY, job.summary_path)

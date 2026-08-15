"""Reading and writing the parquet artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

import configs
from models.instrument import InstrumentSet
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


def catalogued_sets(
    root: Path = configs.ARTIFACTS_ROOT,
) -> list[tuple[str, str, str]]:
    """Return every instrument set the computed artifacts hold anywhere.

    Args:
        root: The artifacts root directory holding the catalogue index.

    Returns:
        The instrument host, instrument, and product type of each set, in the
        order the index first mentions it, and empty when there is no index.
    """
    path = layout.catalog_summary_path(root)
    if not path.exists():
        return []
    table = pq.read_table(path, columns=["ihid", "iid", "pt"])
    return list(
        dict.fromkeys(zip(*(table.column(c).to_pylist() for c in table.schema.names)))
    )


def load_feature(
    feature_class: str,
    name: str,
    root: Path = configs.COVERAGE_ROOT,
    artifacts_root: Path = configs.ARTIFACTS_ROOT,
) -> list[SetCoverage]:
    """Read every instrument set for one feature, observed or not.

    A set that reached this feature is read from its artifacts. A set the
    dataset carries elsewhere but that has no artifact here observed none of
    it, and is returned holding no events, so a figure can say so rather than
    leave the instrument out and let a missing line read as missing data. Its
    summary spans the feature's measured period, which is the axis the flat
    line has to be drawn against; nothing about it is ever written to disk.

    Args:
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.
        root: The coverage artifacts root directory.
        artifacts_root: The artifacts root holding the catalogue index.

    Returns:
        One entry per instrument set, widest coverage first. A run that kept no
        union measured no coverage to rank by, so those sets fall back to the
        busiest first.
    """
    directory = layout.feature_artifacts_dir(root, feature_class, name)
    measured = [
        entry
        for path in sorted(directory.glob(f"*{configs.EVENTS_SUFFIX}"))
        if (entry := _load_set(path))
    ]
    return sorted(
        measured + _unobserved(measured, catalogued_sets(artifacts_root), directory),
        key=lambda entry: (-(entry.summary.covered_frac or 0.0), -entry.summary.n_obs),
    )


def _unobserved(
    measured: Sequence[SetCoverage],
    catalogued: Sequence[tuple[str, str, str]],
    directory: Path,
) -> list[SetCoverage]:
    """Build an empty entry for every set with no measurement of this feature.

    A set with records downloaded but no artifact beside them was never
    measured, and saying it observed nothing would be as misleading as leaving
    it out, so it is marked as still pending instead.

    Args:
        measured: The sets that did reach it, at least one of which is needed
            to know the feature and the period the empty ones are drawn over.
        catalogued: Every instrument set the artifacts hold anywhere.
        directory: The feature's artifacts directory.

    Returns:
        One entry per catalogued set with no measurement here, holding no
        events and no covered ground.
    """
    if not measured:
        return []
    known = {
        (entry.summary.ihid, entry.summary.iid, entry.summary.pt) for entry in measured
    }
    reference = replace(
        measured[0].summary,
        covered_km2=0.0,
        covered_frac=0.0,
        n_obs=0,
        t_first=min(entry.summary.t_first for entry in measured),
        t_last=max(entry.summary.t_last for entry in measured),
        span_days=0.0,
    )
    return [
        SetCoverage(
            events=[],
            summary=replace(reference, ihid=ihid, iid=iid, pt=pt),
            pending=layout.has_metadata(directory, InstrumentSet(ihid, iid, pt)),
        )
        for ihid, iid, pt in catalogued
        if (ihid, iid, pt) not in known
    ]


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

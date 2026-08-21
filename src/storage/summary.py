"""What previous runs produced: the coverage artifacts, and their index."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import utils.paths as paths
from models.instrument import InstrumentSet
from models.results import Event, SetCoverage, Summary
from storage import metadata
from storage.disk import atomic_path
from storage.schemas import EVENTS, SUMMARY
from utils.paths import catalog_summary_path, feature_artifacts_dir


def finalise_feature(feature_dir: Path) -> int:
    """Gather one feature's instrument set summaries into a single file.

    Args:
        feature_dir: The feature's artifacts directory.

    Returns:
        The number of summary rows written, or zero when nothing is finished.
    """
    found = sorted(feature_dir.glob(f"*{paths.SET_SUMMARY_SUFFIX}"))
    if not found:
        return 0
    return _concatenate(found, feature_dir / paths.SUMMARY_NAME)


def reindex() -> int:
    """Rebuild the per-feature and catalogue-wide summaries from disk.

    Returns:
        How many summary rows the catalogue index holds.
    """
    for feature_dir in sorted(paths.COVERAGE_ROOT.glob("*/*")):
        finalise_feature(feature_dir)
    return rebuild(paths.ARTIFACTS_ROOT, paths.COVERAGE_ROOT)


def rebuild(artifacts_root: Path, coverage_root: Path) -> int:
    """Concatenate every per-feature summary into the catalogue index.

    Args:
        artifacts_root: The artifacts root directory the index is written to.
        coverage_root: The directory holding the per-feature artifacts.

    Returns:
        The number of summary rows written.
    """
    found = sorted(coverage_root.glob(f"*/*/{paths.SUMMARY_NAME}"))
    return _concatenate(found, catalog_summary_path(artifacts_root))


def _concatenate(found: list[Path], destination: Path) -> int:
    """Write many summary files out as one, atomically.

    Args:
        found: The summary parquet files to combine, in the order to keep.
        destination: The parquet file to write them to.

    Returns:
        The number of rows written.
    """
    tables = [pq.read_table(path, schema=SUMMARY) for path in found]
    combined = pa.concat_tables(tables) if tables else SUMMARY.empty_table()
    with atomic_path(destination) as tmp:
        pq.write_table(combined, tmp, compression="zstd")
    return combined.num_rows


def computed_features(root: Path = paths.COVERAGE_ROOT) -> set[tuple[str, str]]:
    """Return every feature that has coverage computed locally.

    Args:
        root: The coverage artifacts root directory.

    Returns:
        The class and name slug of each feature holding at least one computed
        instrument set.
    """
    return {
        (path.parent.parent.name, path.parent.name)
        for path in root.glob(f"*/*/*{paths.EVENTS_SUFFIX}")
    }


def catalogued_sets(root: Path = paths.ARTIFACTS_ROOT) -> list[str]:
    """Return every instrument set the computed artifacts hold anywhere.

    Args:
        root: The artifacts root directory holding the catalogue index.

    Returns:
        The identifier of each set, in the order the index first mentions it,
        and empty when there is no index.
    """
    path = catalog_summary_path(root)
    if not path.exists():
        return []
    return list(dict.fromkeys(_summary_table(path).column("set_key").to_pylist()))


def load_feature(
    feature_class: str,
    name: str,
    root: Path = paths.COVERAGE_ROOT,
    artifacts_root: Path = paths.ARTIFACTS_ROOT,
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
        One entry per instrument set, widest coverage first, and the busiest
        first among the sets that reached the same share of it.
    """
    directory = feature_artifacts_dir(root, feature_class, name)
    measured = [
        entry
        for path in sorted(directory.glob(f"*{paths.EVENTS_SUFFIX}"))
        if (entry := _load_set(path))
    ]
    return sorted(
        measured + _unobserved(measured, catalogued_sets(artifacts_root), directory),
        key=lambda entry: (-entry.summary.covered_frac, -entry.summary.n_obs),
    )


def _summary_table(path: Path) -> pa.Table:
    """Read a summary file under the current schema.

    A file written before a column existed simply carries nothing in it, since
    reading under a schema fills what is missing and drops what it does not
    name.

    Args:
        path: The summary parquet file.

    Returns:
        The table, under the current schema.
    """
    return pq.read_table(path, schema=SUMMARY)


def _load_set(events_path: Path) -> SetCoverage | None:
    """Read one instrument set's events and summary.

    Args:
        events_path: The set's events parquet file.

    Returns:
        The set's coverage, or None when its summary is missing, which marks a
        set whose computation never finished.
    """
    summary_path = events_path.with_name(
        events_path.name.replace(paths.EVENTS_SUFFIX, paths.SET_SUMMARY_SUFFIX)
    )
    if not summary_path.exists():
        return None
    summary = _summary_table(summary_path).to_pylist()
    events = pq.read_table(events_path, schema=EVENTS).to_pylist()
    return SetCoverage(
        events=[Event(**row) for row in events], summary=Summary(**summary[0])
    )


def _unobserved(
    measured: Sequence[SetCoverage], catalogued: Sequence[str], directory: Path
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
    known = {entry.summary.set_key for entry in measured}
    reference = replace(
        measured[0].summary,
        covered_km2=0.0,
        covered_frac=0.0,
        n_obs=0,
        pixels=0.0,
        t_first=min(entry.summary.t_first for entry in measured),
        t_last=max(entry.summary.t_last for entry in measured),
        span_days=0.0,
    )
    missing = [InstrumentSet.from_key(key) for key in catalogued if key not in known]
    return [
        SetCoverage(
            events=[],
            summary=replace(
                reference,
                set_key=absent.key,
                ihid=absent.ihid,
                iid=absent.iid,
                pt=absent.pt,
            ),
            pending=metadata.has_metadata(directory, absent),
        )
        for absent in missing
    ]

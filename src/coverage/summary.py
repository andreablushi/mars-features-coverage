"""What previous runs produced: the coverage artifacts, and their index."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import utils.disk.paths as paths
from coverage.results import Event, SetCoverage, Summary
from coverage.schemas import EVENTS, SUMMARY
from metadata import tree
from models.instrument import InstrumentSet
from utils.disk.files import atomic_path
from utils.disk.paths import catalog_summary_path, feature_artifacts_dir


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
        The class and name slug of each feature with a computed instrument set.
    """
    return {
        (path.parent.parent.name, path.parent.name)
        for path in root.glob(f"*/*/*{paths.EVENTS_SUFFIX}")
    }


def catalogued_features(root: Path = paths.ARTIFACTS_ROOT) -> list[tuple[str, str]]:
    """Name every feature the computed artifacts hold, as the catalogue spells it.

    Args:
        root: The artifacts root directory holding the catalogue index.

    Returns:
        The class and name of each feature, once each and in order.
    """
    path = catalog_summary_path(root)
    if not path.exists():
        return []
    table = _summary_table(path)
    named = zip(
        table.column("feature_class").to_pylist(),
        table.column("feature_name").to_pylist(),
        strict=True,
    )
    return sorted(dict.fromkeys(named))


def catalogued_rows(root: Path = paths.ARTIFACTS_ROOT) -> list[Summary]:
    """Read every row the computed artifacts hold anywhere.

    Args:
        root: The artifacts root directory holding the catalogue index.

    Returns:
        One row per feature and instrument set measured, in index order.
    """
    path = catalog_summary_path(root)
    if not path.exists():
        return []
    return [Summary(**row) for row in _summary_table(path).to_pylist()]


def catalogued_sets(root: Path = paths.ARTIFACTS_ROOT) -> list[str]:
    """Return every instrument set the computed artifacts hold anywhere.

    Args:
        root: The artifacts root directory holding the catalogue index.

    Returns:
        The identifier of each set, in the order the index first mentions it.
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

    Args:
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.
        root: The coverage artifacts root directory.
        artifacts_root: The artifacts root holding the catalogue index.

    Returns:
        One entry per instrument set, widest coverage first, then busiest.
    """
    directory = feature_artifacts_dir(root, feature_class, name)
    measured = [
        instrument
        for path in sorted(directory.glob(f"*{paths.EVENTS_SUFFIX}"))
        if (instrument := _load_set(path))
    ]
    return sorted(
        measured + _unobserved(measured, catalogued_sets(artifacts_root), directory),
        key=lambda instrument: (
            -instrument.summary.covered_frac,
            -instrument.summary.n_obs,
        ),
    )


def _summary_table(path: Path) -> pa.Table:
    """Read a summary file under the current schema.

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
        The set's coverage, or None when its summary is missing.
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
    """Build an empty instrument for every set with no measurement of this feature.

    Args:
        measured: The sets that did reach it, at least one of which is needed.
        catalogued: Every instrument set the artifacts hold anywhere.
        directory: The feature's artifacts directory.

    Returns:
        One entry per catalogued set with no measurement here, holding no events.
    """
    if not measured:
        return []
    known = {instrument.summary.set_key for instrument in measured}
    reference = replace(
        measured[0].summary,
        covered_km2=0.0,
        covered_frac=0.0,
        n_obs=0,
        pixels=0.0,
        t_first=min(instrument.summary.t_first for instrument in measured),
        t_last=max(instrument.summary.t_last for instrument in measured),
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
            pending=tree.has_metadata(directory, absent),
        )
        for absent in missing
    ]

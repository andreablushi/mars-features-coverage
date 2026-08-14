"""Assembling per-feature and catalogue-wide summaries from finished sets.

Both indexes are rebuilt by reading what is on disk rather than by collecting
what the current run produced. A run that resumes an earlier one only computes
the sets that were still missing, so anything it held in memory would describe
a fraction of the catalogue.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from analysis import configs
from analysis.loader import layout
from analysis.models.schemas import SUMMARY
from common.files import atomic_path


def finalise_feature(coverage_root: Path, feature_dir: Path) -> int:
    """Gather one feature's instrument set summaries into a single file.

    Args:
        coverage_root: The coverage artifacts root directory.
        feature_dir: The feature's metadata directory.

    Returns:
        The number of summary rows written, or zero when nothing is finished.
    """
    destination = layout.feature_summary_path(coverage_root, feature_dir)
    paths = sorted(destination.parent.glob(f"*{configs.SET_SUMMARY_SUFFIX}"))
    if not paths:
        return 0
    return _concatenate(paths, destination)


def rebuild(artifacts_root: Path, coverage_root: Path) -> int:
    """Concatenate every per-feature summary into the catalogue index.

    Args:
        artifacts_root: The artifacts root directory the index is written to.
        coverage_root: The directory holding the per-feature artifacts.

    Returns:
        The number of summary rows written.
    """
    paths = sorted(coverage_root.glob(f"*/*/{configs.SUMMARY_NAME}"))
    return _concatenate(paths, layout.catalog_summary_path(artifacts_root))


def _concatenate(paths: list[Path], destination: Path) -> int:
    """Write many summary files out as one, atomically.

    Args:
        paths: The summary parquet files to combine, in the order to keep.
        destination: The parquet file to write them to.

    Returns:
        The number of rows written.
    """
    tables = [pq.read_table(path, schema=SUMMARY) for path in paths]
    combined = pa.concat_tables(tables) if tables else SUMMARY.empty_table()
    with atomic_path(destination) as tmp:
        pq.write_table(combined, tmp, compression="zstd")
    return combined.num_rows

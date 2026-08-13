"""Assembling the catalogue-wide summary from the per-feature ones.

The index is rebuilt by reading what is on disk rather than by collecting what
the current run produced. A run that resumes an earlier one only computes the
features that were still missing, so anything it held in memory would describe
a fraction of the catalogue.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from analysis import configs
from analysis.loader import layout, schemas
from common.atomic import atomic_path


def rebuild(artifacts_root: Path, coverage_root: Path) -> int:
    """Concatenate every per-feature summary into the catalogue index.

    Args:
        artifacts_root: The artifacts root directory the index is written to.
        coverage_root: The directory holding the per-feature artifacts.

    Returns:
        The number of summary rows written.
    """
    paths = sorted(coverage_root.glob(f"*/*/{configs.SUMMARY_NAME}"))
    tables = [pq.read_table(path, schema=schemas.SUMMARY) for path in paths]
    combined = pa.concat_tables(tables) if tables else schemas.SUMMARY.empty_table()
    with atomic_path(layout.catalog_summary_path(artifacts_root)) as tmp:
        pq.write_table(combined, tmp, compression="zstd")
    return combined.num_rows

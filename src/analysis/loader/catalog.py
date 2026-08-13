"""Assembling per-feature and catalogue-wide summaries from finished sets.

Both indexes are rebuilt by reading what is on disk rather than by collecting
what the current run produced. A run that resumes an earlier one only computes
the sets that were still missing, so anything it held in memory would describe
a fraction of the catalogue.

The pooled row is the union of a feature's finished instrument sets, which is
exactly the union of their observations, so it costs one combine rather than a
second pass over every footprint.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from shapely import from_wkb, union_all

from analysis import configs
from analysis.computation.coverage import summarise
from analysis.loader import layout, writer
from analysis.models.schemas import SUMMARY
from common.atomic import atomic_path

_SET_SUMMARY_SUFFIX = ".summary.parquet"
_SET_UNION_SUFFIX = ".union.wkb"


def finalise_feature(coverage_root: Path, feature_dir: Path) -> int:
    """Combine one feature's set summaries and add the pooled row.

    Args:
        coverage_root: The coverage artifacts root directory.
        feature_dir: The feature's metadata directory.

    Returns:
        The number of summary rows written, or zero when nothing is finished.
    """
    destination = layout.feature_summary_path(coverage_root, feature_dir)
    pairs = [
        (path, pq.read_table(path, schema=SUMMARY).to_pylist())
        for path in sorted(destination.parent.glob(f"*{_SET_SUMMARY_SUFFIX}"))
    ]
    rows = [row for _, batch in pairs for row in batch]
    if not rows:
        return 0
    rows.append(_pooled(pairs, rows))
    writer.write_rows(rows, SUMMARY, destination)
    return len(rows)


def _pooled(
    pairs: list[tuple[Path, list[dict[str, Any]]]], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build the row pooling every non-basemap set of one feature.

    Whole-planet basemaps are left out. Including them would put the row at
    full coverage regardless and say nothing about what the targeted
    instruments actually reached.

    Args:
        pairs: Each set's summary file and the rows read from it, so a set's
            union can be found by name rather than by directory order.
        rows: Every set summary row, flattened.

    Returns:
        The pooled summary row.
    """
    shapes = []
    targeted: list[dict[str, Any]] = []
    for path, batch in pairs:
        if any(row["gridded"] for row in batch):
            continue
        targeted.extend(batch)
        union_file = path.with_name(
            path.name[: -len(_SET_SUMMARY_SUFFIX)] + _SET_UNION_SUFFIX
        )
        if union_file.exists():
            shapes.append(from_wkb(union_file.read_bytes()))

    label = configs.ALL_SETS_LABEL
    starts = [row["t_first"] for row in targeted if row["t_first"]]
    ends = [row["t_last"] for row in targeted if row["t_last"]]
    return asdict(
        summarise(
            rows[0]["feature_class"],
            rows[0]["feature_name"],
            (label, label, label),
            rows[0]["feature_area_km2"] * 1e6,
            union_all(shapes).area if shapes else 0.0,
            sum(row["n_obs"] for row in targeted),
            None,
            min(starts) if starts else None,
            max(ends) if ends else None,
            False,
        )
    )


def rebuild(artifacts_root: Path, coverage_root: Path) -> int:
    """Concatenate every per-feature summary into the catalogue index.

    Args:
        artifacts_root: The artifacts root directory the index is written to.
        coverage_root: The directory holding the per-feature artifacts.

    Returns:
        The number of summary rows written.
    """
    paths = sorted(coverage_root.glob(f"*/*/{configs.SUMMARY_NAME}"))
    tables = [pq.read_table(path, schema=SUMMARY) for path in paths]
    combined = pa.concat_tables(tables) if tables else SUMMARY.empty_table()
    with atomic_path(layout.catalog_summary_path(artifacts_root)) as tmp:
        pq.write_table(combined, tmp, compression="zstd")
    return combined.num_rows

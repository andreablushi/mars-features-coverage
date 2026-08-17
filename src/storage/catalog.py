"""Assembling per-feature and catalogue-wide summaries from finished sets."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import configs
from models.feature import Feature
from models.product import InstrumentSetInfo
from storage import layout
from storage.files import atomic_path, read_jsonl
from storage.schemas import SUMMARY


def finalise_feature(feature_dir: Path) -> int:
    """Gather one feature's instrument set summaries into a single file.

    The feature is read from the artifacts alone, so an index can be rebuilt
    after the metadata that produced it has been discarded.

    Args:
        feature_dir: The feature's artifacts directory.

    Returns:
        The number of summary rows written, or zero when nothing is finished.
    """
    paths = sorted(feature_dir.glob(f"*{configs.SET_SUMMARY_SUFFIX}"))
    if not paths:
        return 0
    return _concatenate(paths, feature_dir / configs.SUMMARY_NAME)


def reindex() -> int:
    """Rebuild the per-feature and catalogue-wide summaries from disk.

    Returns:
        How many summary rows the catalogue index holds.
    """
    for feature_dir in sorted(configs.COVERAGE_ROOT.glob("*/*")):
        finalise_feature(feature_dir)
    return rebuild(configs.ARTIFACTS_ROOT, configs.COVERAGE_ROOT)


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


def features_path(cache_dir: Path = configs.CATALOG_ROOT) -> Path:
    """Return where the cached feature catalogue lives.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        The path to the features JSONL file, which need not exist.
    """
    return cache_dir / configs.FEATURES_CACHE_NAME


def instrument_sets_path(cache_dir: Path = configs.CATALOG_ROOT) -> Path:
    """Return where the cached instrument set catalogue lives.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        The path to the instrument sets JSONL file, which need not exist.
    """
    return cache_dir / configs.INSTRUMENT_SETS_CACHE_NAME


def read_features(cache_dir: Path = configs.CATALOG_ROOT) -> list[Feature]:
    """Read the cached geological feature catalogue.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        Every catalogued feature.
    """
    return [Feature(**row) for row in read_jsonl(features_path(cache_dir))]


def read_instrument_sets(
    cache_dir: Path = configs.CATALOG_ROOT,
) -> list[InstrumentSetInfo]:
    """Read the cached instrument set catalogue.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        One entry per unique instrument set.
    """
    return [
        InstrumentSetInfo(**row) for row in read_jsonl(instrument_sets_path(cache_dir))
    ]

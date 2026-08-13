"""Filesystem layout for computed coverage artifacts.

The artifact tree mirrors the metadata tree it is derived from, so plotting one
feature means opening one small directory instead of filtering a single table
holding every feature in the catalogue. Because both trees are keyed by the
same class and name slugs, a feature's artifact paths follow from its metadata
path alone, without reading anything inside it.
"""

from __future__ import annotations

from pathlib import Path

from analysis import configs


def _feature_dir(root: Path, feature_dir: Path) -> Path:
    """Return the directory holding one feature's artifacts under a root.

    Args:
        root: The artifacts subtree the path is built under.
        feature_dir: The feature's metadata directory.

    Returns:
        The matching path under the given root.
    """
    return root / feature_dir.parent.name / feature_dir.name


def events_path(root: Path, source: Path) -> Path:
    """Return the per-observation events file for one instrument set.

    Args:
        root: The coverage artifacts root directory.
        source: The instrument set's metadata JSONL file.

    Returns:
        The path to the events parquet file.
    """
    return _feature_dir(root, source.parent) / f"{source.stem}.events.parquet"


def set_summary_path(root: Path, source: Path) -> Path:
    """Return the summary file for one instrument set.

    It is written after the events, so its presence is what marks a set as
    fully computed when a later run decides what to skip.

    Args:
        root: The coverage artifacts root directory.
        source: The instrument set's metadata JSONL file.

    Returns:
        The path to the summary parquet file.
    """
    return _feature_dir(root, source.parent) / f"{source.stem}.summary.parquet"


def geometry_path(root: Path, source: Path) -> Path:
    """Return the cached projected footprints for one instrument set.

    Args:
        root: The geometry cache root directory.
        source: The instrument set's metadata JSONL file.

    Returns:
        The path to the geometry cache parquet file.
    """
    return _feature_dir(root, source.parent) / f"{source.stem}.parquet"


def feature_summary_path(root: Path, feature_dir: Path) -> Path:
    """Return one feature's combined summary, pooled row included.

    Args:
        root: The coverage artifacts root directory.
        feature_dir: The feature's metadata directory.

    Returns:
        The path to the summary parquet file.
    """
    return _feature_dir(root, feature_dir) / configs.SUMMARY_NAME


def catalog_summary_path(root: Path) -> Path:
    """Return the file holding every feature's summary rows together.

    Args:
        root: The artifacts root directory.

    Returns:
        The path to the catalogue-wide summary parquet file.
    """
    return root / configs.SUMMARY_NAME

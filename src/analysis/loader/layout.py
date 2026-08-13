"""Filesystem layout for computed coverage artifacts.

The artifact tree mirrors the metadata tree it is derived from, so plotting one
feature means opening one small directory instead of filtering a single table
holding every feature in the catalogue. Because both trees are keyed by the
same class and name slugs, a feature's artifact paths follow from its metadata
directory alone, without reading anything inside it.
"""

from __future__ import annotations

from pathlib import Path

from analysis import configs


def artifact_dir(root: Path, source: Path) -> Path:
    """Return the directory holding one feature's coverage artifacts.

    Args:
        root: The coverage artifacts root directory.
        source: The feature's metadata directory.

    Returns:
        The matching path under the artifacts root.
    """
    return root / source.parent.name / source.name


def events_path(root: Path, source: Path) -> Path:
    """Return the per-observation events file for one feature.

    Args:
        root: The coverage artifacts root directory.
        source: The feature's metadata directory.

    Returns:
        The path to the events parquet file.
    """
    return artifact_dir(root, source) / configs.EVENTS_NAME


def summary_path(root: Path, source: Path) -> Path:
    """Return the per-instrument-set summary file for one feature.

    The summary is written after the events, so its presence is what marks a
    feature as fully computed when a later run decides what to skip.

    Args:
        root: The coverage artifacts root directory.
        source: The feature's metadata directory.

    Returns:
        The path to the summary parquet file.
    """
    return artifact_dir(root, source) / configs.SUMMARY_NAME


def catalog_summary_path(root: Path) -> Path:
    """Return the file holding every feature's summary rows together.

    Args:
        root: The artifacts root directory.

    Returns:
        The path to the catalogue-wide summary parquet file.
    """
    return root / configs.SUMMARY_NAME

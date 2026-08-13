"""Filesystem layout for computed coverage artifacts.

The artifact tree mirrors the metadata tree it is derived from, so plotting one
feature means opening one small directory instead of filtering a single table
holding every feature in the catalogue.
"""

from __future__ import annotations

from pathlib import Path

from analysis import configs
from download.storage.layout import slugify


def catalog_summary_path(root: Path) -> Path:
    """Return the file holding every feature's summary rows together.

    Args:
        root: The artifacts root directory.

    Returns:
        The path to the catalogue-wide summary parquet file.
    """
    return root / configs.SUMMARY_NAME


def feature_dir(root: Path, feature_class: str, feature_name: str) -> Path:
    """Return the directory holding one feature's coverage artifacts.

    Args:
        root: The coverage artifacts root directory.
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.

    Returns:
        The path root/<class-slug>/<name-slug>.
    """
    return root / slugify(feature_class) / slugify(feature_name)


def events_path(root: Path, feature_class: str, feature_name: str) -> Path:
    """Return the per-observation events file for one feature.

    Args:
        root: The coverage artifacts root directory.
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.

    Returns:
        The path to the events parquet file.
    """
    return feature_dir(root, feature_class, feature_name) / configs.EVENTS_NAME


def summary_path(root: Path, feature_class: str, feature_name: str) -> Path:
    """Return the per-instrument-set summary file for one feature.

    Args:
        root: The coverage artifacts root directory.
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.

    Returns:
        The path to the summary parquet file.
    """
    return feature_dir(root, feature_class, feature_name) / configs.SUMMARY_NAME

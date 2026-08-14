"""Filesystem layout: output paths for downloaded metadata.

The coverage stage keys its own artifact tree off the directory names written
here, so it mirrors this layout by reusing the same slug rule.
"""

from __future__ import annotations

from pathlib import Path

from common.files import slugify
from download.models.feature import Feature
from download.models.instrument import InstrumentSet


def feature_dir(root: Path, feature: Feature) -> Path:
    """Return the directory that holds a feature's metadata files.

    Args:
        root: The metadata root directory.
        feature: The feature being stored.

    Returns:
        The path root/<class-slug>/<name-slug>.
    """
    return root / slugify(feature.feature_class) / slugify(feature.name)


def product_file(root: Path, feature: Feature, instrument_set: InstrumentSet) -> Path:
    """Return the JSONL path for one feature and instrument set.

    Args:
        root: The metadata root directory.
        feature: The feature being stored.
        instrument_set: The instrument set being stored.

    Returns:
        The path to the JSONL output file.
    """
    return feature_dir(root, feature) / f"{instrument_set.slug}.jsonl"

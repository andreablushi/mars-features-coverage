"""Filesystem layout: output paths for downloaded metadata."""

from __future__ import annotations

from pathlib import Path

from common.paths import feature_dir
from download.models.feature import Feature
from download.models.instrument import InstrumentSet


def product_file(root: Path, feature: Feature, instrument_set: InstrumentSet) -> Path:
    """Return the JSONL path for one feature and instrument set.

    Args:
        root: The metadata root directory.
        feature: The feature being stored.
        instrument_set: The instrument set being stored.

    Returns:
        The path to the JSONL output file.
    """
    directory = feature_dir(root, feature.feature_class, feature.name)
    return directory / f"{instrument_set.slug}.jsonl"

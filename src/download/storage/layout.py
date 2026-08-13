"""Filesystem layout: slugs and output paths for downloaded metadata.

The coverage stage keys its own artifact tree off the directory names written
here, so it mirrors this layout without needing to slugify anything itself.
"""

from __future__ import annotations

import re
from pathlib import Path

from download.models.feature import Feature
from download.models.instrument import InstrumentSet

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Convert a name into a lowercase, underscore separated slug.

    Args:
        text: The raw name, for example "Rovers and Landers".

    Returns:
        A slug such as "rovers_and_landers", or "unnamed" if empty.
    """
    slug = _SLUG_RE.sub("_", text.strip().lower()).strip("_")
    return slug or "unnamed"


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

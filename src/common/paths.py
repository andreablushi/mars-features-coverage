"""Filesystem naming shared by every stage.

Both stages lay their output out as <class-slug>/<name-slug>, so the artifact
tree mirrors the metadata tree and a feature can be found in either by the same
pair of slugs.
"""

from __future__ import annotations

import re
from pathlib import Path

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


def feature_dir(root: Path, feature_class: str, feature_name: str) -> Path:
    """Return the directory holding one feature's files under a root.

    Args:
        root: The root directory the tree hangs off.
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.

    Returns:
        The path root/<class-slug>/<name-slug>.
    """
    return root / slugify(feature_class) / slugify(feature_name)

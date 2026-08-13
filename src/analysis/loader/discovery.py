"""Finding the features that have metadata worth computing.

The download stage writes an output file for every feature and instrument set
it queries, empty ones included, so that a resumed download can tell what it
already asked for. An empty file means the instrument never saw the feature,
so a directory holding nothing but empty files has no coverage to measure.
"""

from __future__ import annotations

from pathlib import Path

from analysis import configs


def find_features(root: Path = configs.METADATA_ROOT) -> list[Path]:
    """Find every feature directory holding downloaded observations.

    Args:
        root: The metadata root directory.

    Returns:
        The feature directories, sorted, that hold at least one non-empty
        JSONL file.
    """
    return sorted(path for path in root.glob("*/*") if _has_records(path))


def _has_records(path: Path) -> bool:
    """Report whether a directory holds any downloaded observations.

    Args:
        path: The candidate feature directory.

    Returns:
        True when the path is a directory with a non-empty JSONL file in it.
    """
    return path.is_dir() and any(
        file.stat().st_size > 0 for file in path.glob("*.jsonl")
    )

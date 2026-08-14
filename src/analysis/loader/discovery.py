"""Finding the instrument sets that have metadata worth computing.

The download stage writes an output file for every feature and instrument set
it queries, empty ones included, so that a resumed download can tell what it
already asked for. An empty file means the instrument never saw the feature,
so it has no coverage to measure.
"""

from __future__ import annotations

from pathlib import Path

from analysis import configs


def find_sets(root: Path = configs.METADATA_ROOT) -> list[Path]:
    """Find every stored instrument set holding observations.

    Args:
        root: The metadata root directory.

    Returns:
        The non-empty JSONL files, sorted, one per feature and instrument set.
    """
    return sorted(path for path in root.glob("*/*/*.jsonl") if path.stat().st_size > 0)

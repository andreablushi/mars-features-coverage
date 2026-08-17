"""What the downloaded metadata tree holds, and what to drop from it."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import configs
from models.instrument import InstrumentSet
from models.job import Outcome


def find_sets(root: Path = configs.METADATA_ROOT) -> list[Path]:
    """Find every stored instrument set holding observations.

    Args:
        root: The metadata root directory.

    Returns:
        The non-empty JSONL files, sorted, one per feature and instrument set.
    """
    return sorted(path for path in root.glob("*/*/*.jsonl") if path.stat().st_size > 0)


def has_metadata(
    feature_dir: Path, instrument_set: InstrumentSet, root: Path = configs.METADATA_ROOT
) -> bool:
    """Report whether one feature holds downloaded records for an instrument set.

    Args:
        feature_dir: The feature's artifacts directory
        instrument_set: The instrument set to look for.
        root: The metadata root directory.

    Returns:
        True when a non-empty metadata file for that set exists.
    """
    directory = root / feature_dir.parent.name / feature_dir.name
    return any(
        path.stat().st_size > 0
        for path in directory.glob(f"{instrument_set.slug}*.jsonl")
    )


def discard_metadata(outcomes: Sequence[Outcome]) -> int:
    """Delete the metadata of every set whose coverage is now on disk.

    Args:
        outcomes: Every finished coverage job.

    Returns:
        How many metadata files were removed.
    """
    removed = 0
    for outcome in outcomes:
        if not outcome.failed and outcome.job.summary_path.exists():
            outcome.job.source.unlink(missing_ok=True)
            removed += 1
    return removed

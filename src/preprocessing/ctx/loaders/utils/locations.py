"""Where the files of one CTX observation are kept on disk."""

from __future__ import annotations

from pathlib import Path

from preprocessing.ctx import configs
from preprocessing.ctx.loaders.utils import naming


def files(observation_id: str) -> dict[str, Path]:
    """Return where each product of one scan belongs.

    Args:
        observation_id: The observation, such as P01_001393_1655_XN_14S149W.

    Returns:
        The path for each kind, keyed by kind.
    """
    place = configs.CACHE_ROOT / observation_id
    return {
        kind: place / f"{observation_id}{suffix}"
        for kind, suffix in naming.SUFFIXES.items()
    }


def label(observation_id: str) -> Path:
    """Return where one scan's label belongs.

    Args:
        observation_id: The observation.

    Returns:
        The label path, whose image sits beside it.
    """
    return files(observation_id)[naming.LABEL]

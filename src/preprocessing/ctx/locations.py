"""Where the files of one CTX observation are kept on disk."""

from __future__ import annotations

from pathlib import Path

from preprocessing.common.locations import product_files
from preprocessing.ctx import configs, naming


def files(observation_id: str) -> dict[str, Path]:
    """Return where each product of one scan belongs.

    Args:
        observation_id: The observation, such as P01_001393_1655_XN_14S149W.

    Returns:
        The path for each suffix, keyed by suffix. ASU names both products
        after the scan itself, so the suffix is all that tells them apart.
    """
    return product_files(
        configs.CACHE_ROOT,
        observation_id,
        observation_id,
        naming.SUFFIXES.values(),
    )


def image(observation_id: str) -> Path:
    """Return where one scan's projected image belongs.

    Args:
        observation_id: The observation.

    Returns:
        The image path, whose label sits beside it.
    """
    return files(observation_id)[naming.SUFFIXES[naming.IMAGE]]


def label(observation_id: str) -> Path:
    """Return where one scan's label belongs.

    Args:
        observation_id: The observation.

    Returns:
        The label path, whose image sits beside it.
    """
    return files(observation_id)[naming.SUFFIXES[naming.LABEL]]

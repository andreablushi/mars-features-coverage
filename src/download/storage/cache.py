"""Reading the cached ODE catalogues off disk.

The catalogues are fetched once and kept, so anything that needs to know which
features or instrument sets exist can read them without a client and without a
network call.
"""

from __future__ import annotations

from pathlib import Path

from common.files import read_jsonl
from download import configs
from download.models.feature import Feature
from download.models.product import InstrumentSetInfo


def features_path(cache_dir: Path = configs.CATALOG_ROOT) -> Path:
    """Return where the cached feature catalogue lives.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        The path to the features JSONL file, which need not exist.
    """
    return cache_dir / configs.FEATURES_CACHE_NAME


def instrument_sets_path(cache_dir: Path = configs.CATALOG_ROOT) -> Path:
    """Return where the cached instrument set catalogue lives.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        The path to the instrument sets JSONL file, which need not exist.
    """
    return cache_dir / configs.INSTRUMENT_SETS_CACHE_NAME


def read_features(cache_dir: Path = configs.CATALOG_ROOT) -> list[Feature]:
    """Read the cached geological feature catalogue.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        Every catalogued feature.
    """
    return [Feature(**row) for row in read_jsonl(features_path(cache_dir))]


def read_instrument_sets(
    cache_dir: Path = configs.CATALOG_ROOT,
) -> list[InstrumentSetInfo]:
    """Read the cached instrument set catalogue.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        One entry per unique instrument set.
    """
    return [
        InstrumentSetInfo(**row) for row in read_jsonl(instrument_sets_path(cache_dir))
    ]

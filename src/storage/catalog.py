"""Reading the cached ODE feature and instrument set catalogues."""

from __future__ import annotations

from pathlib import Path

import configs
from models.feature import Feature
from models.instrument import InstrumentSetInfo
from storage.disk import read_jsonl
from storage.paths import features_path, instrument_sets_path


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

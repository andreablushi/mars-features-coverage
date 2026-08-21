"""Reading the cached ODE feature and instrument set catalogues."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import utils.disk.paths as paths
from download.api import catalog as ode
from download.api.client import ODEClient
from models.feature import Feature
from models.instrument import InstrumentSetInfo
from storage.disk import read_jsonl, write_jsonl
from utils.disk.paths import features_path, instrument_sets_path


def read_features(cache_dir: Path = paths.CATALOG_ROOT) -> list[Feature]:
    """Read the cached geological feature catalogue.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        Every catalogued feature.
    """
    return [Feature(**row) for row in read_jsonl(features_path(cache_dir))]


def read_instrument_sets(
    cache_dir: Path = paths.CATALOG_ROOT,
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


def load_features(
    client: ODEClient,
    cache_dir: Path = paths.CATALOG_ROOT,
    *,
    refresh: bool = False,
) -> list[Feature]:
    """Load the geological feature catalog from cache, fetching and caching on a miss.

    Args:
        client: The ODE client to query with.
        cache_dir: Directory holding the cached catalog files.
        refresh: When True, always re-fetch and overwrite the cache.

    Returns:
        The list of features.
    """
    path = features_path(cache_dir)
    if path.exists() and not refresh:
        return read_features(cache_dir)
    features = ode.fetch_features(client)
    write_jsonl(path, [asdict(feature) for feature in features])
    return features


def load_instrument_sets(
    client: ODEClient,
    cache_dir: Path = paths.CATALOG_ROOT,
    *,
    refresh: bool = False,
) -> list[InstrumentSetInfo]:
    """Load the instrument catalog from cache, fetching and caching on a miss.

    Args:
        client: The ODE client to query with.
        cache_dir: Directory holding the cached catalog files.
        refresh: When True, always re-fetch and overwrite the cache.

    Returns:
        One entry per unique instrument set.
    """
    path = instrument_sets_path(cache_dir)
    if path.exists() and not refresh:
        return read_instrument_sets(cache_dir)
    rows = ode.fetch_instrument_sets(client)
    write_jsonl(path, [asdict(row) for row in rows])
    return rows

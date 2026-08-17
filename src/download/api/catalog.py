"""Fetch and cache the ODE feature and instrument catalogs."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import configs as root_configs
from download import configs
from download.api.client import ODEClient, as_items
from download.selection.dedupe import dedupe
from models.feature import Feature
from models.product import InstrumentSetInfo
from storage import catalog, paths
from storage.disk import write_jsonl


def fetch_features(client: ODEClient) -> list[Feature]:
    """Fetch the full Mars feature catalog from ODE, deduplicated.

    Args:
        client: The ODE client to query with.

    Returns:
        The list of unique features.
    """
    results = client.query({"query": "featuredata", "odemetadb": configs.ODE_META_DB})
    raw = as_items(results, "Features", "Feature")
    features = [
        Feature(
            name=item["FeatureName"],
            feature_class=item["FeatureClass"],
            min_lat=float(item["MinLat"]),
            max_lat=float(item["MaxLat"]),
            west_lon=float(item["WestLon"]),
            east_lon=float(item["EastLon"]),
        )
        for item in raw
    ]
    return dedupe(features, key=lambda feature: feature)


def fetch_instrument_sets(client: ODEClient) -> list[InstrumentSetInfo]:
    """Fetch the Mars IIPT catalog from ODE, deduplicated on the triple.

    The raw IIPT list repeats an IHID/IID/PT triple once per data set, so rows
    are collapsed to the unique instrument host, instrument, and product type.

    Args:
        client: The ODE client to query with.

    Returns:
        One entry per unique instrument set, with availability flags.
    """
    results = client.query({"query": "iipt", "odemetadb": configs.ODE_META_DB})
    raw = as_items(results, "IIPTSets", "IIPTSet")
    unique = dedupe(
        raw, key=lambda item: (item.get("IHID"), item.get("IID"), item.get("PT"))
    )
    rows: list[InstrumentSetInfo] = []
    for item in unique:
        number = item.get("NumberProducts")
        rows.append(
            InstrumentSetInfo(
                ihid=item.get("IHID"),
                iid=item.get("IID"),
                pt=item.get("PT"),
                instrument_name=item.get("IName"),
                product_type_name=item.get("PTName"),
                valid_footprints=item.get("ValidFootprints") == "T",
                valid_observation_times=item.get("ValidObservationTimes") == "T",
                number_products=int(number) if number else None,
            )
        )
    return rows


def load_features(
    client: ODEClient,
    cache_dir: Path = root_configs.CATALOG_ROOT,
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
    path = paths.features_path(cache_dir)
    if path.exists() and not refresh:
        return catalog.read_features(cache_dir)
    features = fetch_features(client)
    write_jsonl(path, [asdict(feature) for feature in features])
    return features


def load_instrument_sets(
    client: ODEClient,
    cache_dir: Path = root_configs.CATALOG_ROOT,
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
    path = paths.instrument_sets_path(cache_dir)
    if path.exists() and not refresh:
        return catalog.read_instrument_sets(cache_dir)
    rows = fetch_instrument_sets(client)
    write_jsonl(path, [asdict(row) for row in rows])
    return rows

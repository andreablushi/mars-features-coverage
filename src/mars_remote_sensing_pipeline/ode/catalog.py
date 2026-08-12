"""Fetch and cache the ODE feature and instrument catalogs."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from mars_remote_sensing_pipeline.ode.client import ODEClient, as_list
from mars_remote_sensing_pipeline.ode.models import Feature
from mars_remote_sensing_pipeline.storage.writer import read_jsonl, write_jsonl

_TARGET_DB = "mars"


def fetch_features(client: ODEClient) -> list[Feature]:
    """Fetch the full Mars feature catalog from ODE, deduplicated.

    Args:
        client: The ODE client to query with.

    Returns:
        The list of unique features.
    """
    results = client.query({"query": "featuredata", "odemetadb": _TARGET_DB})
    raw = as_list(results.get("Features", {}).get("Feature"))
    seen: set[Feature] = set()
    features: list[Feature] = []
    for item in raw:
        feature = Feature(
            name=item["FeatureName"],
            feature_class=item["FeatureClass"],
            min_lat=float(item["MinLat"]),
            max_lat=float(item["MaxLat"]),
            west_lon=float(item["WestLon"]),
            east_lon=float(item["EastLon"]),
        )
        if feature in seen:
            continue
        seen.add(feature)
        features.append(feature)
    return features


def fetch_instrument_sets(client: ODEClient) -> list[dict[str, Any]]:
    """Fetch the Mars IIPT catalog from ODE, deduplicated on the triple.

    The raw IIPT list repeats an IHID/IID/PT triple once per data set, so rows
    are collapsed to the unique instrument host, instrument, and product type.

    Args:
        client: The ODE client to query with.

    Returns:
        One dictionary per unique instrument set, with availability flags.
    """
    results = client.query({"query": "iipt", "odemetadb": _TARGET_DB})
    raw = as_list(results.get("IIPTSets", {}).get("IIPTSet"))
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, Any]] = []
    for item in raw:
        triple = (item.get("IHID"), item.get("IID"), item.get("PT"))
        if triple in seen:
            continue
        seen.add(triple)
        number = item.get("NumberProducts")
        rows.append(
            {
                "ihid": item.get("IHID"),
                "iid": item.get("IID"),
                "pt": item.get("PT"),
                "instrument_name": item.get("IName"),
                "product_type_name": item.get("PTName"),
                "valid_footprints": item.get("ValidFootprints") == "T",
                "valid_observation_times": item.get("ValidObservationTimes") == "T",
                "number_products": int(number) if number else None,
            }
        )
    return rows


def load_features(
    client: ODEClient, cache_dir: Path, *, refresh: bool = False
) -> list[Feature]:
    """Load the feature catalog from cache, fetching and caching on a miss.

    Args:
        client: The ODE client to query with.
        cache_dir: Directory holding the cached catalog files.
        refresh: When True, always re-fetch and overwrite the cache.

    Returns:
        The list of features.
    """
    path = cache_dir / "features.jsonl"
    if path.exists() and not refresh:
        return [Feature(**row) for row in read_jsonl(path)]
    features = fetch_features(client)
    write_jsonl(path, [asdict(feature) for feature in features])
    return features


def load_instrument_sets(
    client: ODEClient, cache_dir: Path, *, refresh: bool = False
) -> list[dict[str, Any]]:
    """Load the instrument catalog from cache, fetching and caching on a miss.

    Args:
        client: The ODE client to query with.
        cache_dir: Directory holding the cached catalog files.
        refresh: When True, always re-fetch and overwrite the cache.

    Returns:
        One dictionary per unique instrument set.
    """
    path = cache_dir / "instrument_sets.jsonl"
    if path.exists() and not refresh:
        return list(read_jsonl(path))
    rows = fetch_instrument_sets(client)
    write_jsonl(path, rows)
    return rows

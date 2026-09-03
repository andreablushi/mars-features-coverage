"""Fetch the ODE feature catalog."""

from __future__ import annotations

from analysis.metadata.fetchers.response import as_items
from analysis.models.feature import Feature
from utils.ode import configs
from utils.ode.client import ODEClient


def fetch_features(client: ODEClient) -> list[Feature]:
    """Fetch the full Mars feature catalog from ODE, deduplicated.

    Args:
        client: The ODE client to query with.

    Returns:
        The list of unique features.
    """
    results = client.query({"query": "featuredata", "odemetadb": configs.ODE_META_DB})
    features: list[Feature] = []
    # ODE publishes a feature twice; the first spelling of each one is kept
    seen: set[Feature] = set()
    for item in as_items(results, "Features", "Feature"):
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

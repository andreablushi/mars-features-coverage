"""Fetch the ODE feature and instrument catalogs."""

from __future__ import annotations

from analysis.metadata.api.response import as_items
from analysis.metadata.selection.dedupe import dedupe
from analysis.models.feature import Feature
from analysis.models.instrument import InstrumentSetInfo
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

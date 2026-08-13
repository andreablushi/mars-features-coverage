"""Product metadata queries for one feature and instrument set."""

from __future__ import annotations

from datetime import datetime, timezone

from download import configs
from download.models import Feature, InstrumentSet, ProductRecord
from download.ode.client import ODEClient, as_list
from download.selection import retain_fields


def _base_params(feature: Feature, instrument_set: InstrumentSet) -> dict[str, str]:
    """Build the shared product query parameters for a feature and set.

    Args:
        feature: The feature whose name sets the query bounding box.
        instrument_set: The instrument host, instrument, and product type.

    Returns:
        The parameter dictionary without a results selector.
    """
    return {
        "query": "product",
        "target": configs.ODE_TARGET,
        "ihid": instrument_set.ihid,
        "iid": instrument_set.iid,
        "pt": instrument_set.pt,
        "featurename": feature.name,
        "loc": configs.DEFAULT_LOC,
    }


def count(client: ODEClient, feature: Feature, instrument_set: InstrumentSet) -> int:
    """Return how many products match a feature and instrument set.

    Args:
        client: The ODE client to query with.
        feature: The feature whose name sets the query bounding box.
        instrument_set: The instrument host, instrument, and product type.

    Returns:
        The product count.
    """
    params = _base_params(feature, instrument_set)
    params["results"] = "c"
    results = client.query(params)
    return int(results.get("Count", 0))


def fetch_products(
    client: ODEClient,
    feature: Feature,
    instrument_set: InstrumentSet,
    *,
    total: int | None = None,
) -> list[ProductRecord]:
    """Fetch all product metadata for a feature and instrument set.

    Each record keeps the retained ODE fields plus provenance describing the
    feature, its bounding box, and when the record was retrieved. Coordinates
    are stored exactly as ODE returns them, in degrees.

    ODE offset paging is only stable when a sort order is given, so a fixed
    order is requested and records are deduplicated by product id and gathered
    until the authoritative count is reached. This tolerates the occasional
    duplicate ODE returns at a page boundary. The deduplication runs while
    paging rather than through selection.dedupe, so a large feature never holds
    every raw page in memory at once.

    Args:
        client: The ODE client to query with.
        feature: The feature whose name sets the query bounding box.
        instrument_set: The instrument host, instrument, and product type.
        total: The known product count, fetched if not given.

    Returns:
        One deduplicated record per product.
    """
    if total is None:
        total = count(client, feature, instrument_set)
    if total == 0:
        return []
    provenance = {
        "feature_name": feature.name,
        "feature_class": feature.feature_class,
        "feature_min_lat": feature.min_lat,
        "feature_max_lat": feature.max_lat,
        "feature_west_lon": feature.west_lon,
        "feature_east_lon": feature.east_lon,
        "loc_mode": configs.DEFAULT_LOC,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    records: list[ProductRecord] = []
    seen: set[str] = set()
    offset = 0
    while len(seen) < total:
        params = _base_params(feature, instrument_set)
        params.update(
            {
                "results": "opm",
                "order": configs.PAGE_ORDER,
                "limit": str(configs.PAGE_SIZE),
                "offset": str(offset),
            }
        )
        items = as_list(client.query(params).get("Products", {}).get("Product"))
        if not items:
            break
        added = 0
        for item in items:
            key = str(item.get("pdsid") or item.get("ode_id"))
            if key in seen:
                continue
            seen.add(key)
            records.append(retain_fields(item) | provenance)
            added += 1
        if added == 0:
            break
        offset += len(items)
    return records

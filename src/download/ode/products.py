"""Product metadata queries for one feature and instrument set."""

from __future__ import annotations

from datetime import datetime, timezone

from download import configs
from download.models import Feature, InstrumentSet, ProductRecord
from download.ode.client import ODEClient, as_list


def _base_params(
    feature: Feature,
    instrument_set: InstrumentSet,
    loc: str,
    min_obs_time: str | None,
    max_obs_time: str | None,
) -> dict[str, str]:
    """Build the shared product query parameters for a feature and set.

    Args:
        feature: The feature whose name sets the query bounding box.
        instrument_set: The instrument host, instrument, and product type.
        loc: The ODE containment mode.
        min_obs_time: Optional minimum UTC observation time.
        max_obs_time: Optional maximum UTC observation time.

    Returns:
        The parameter dictionary without a results selector.
    """
    params = {
        "query": "product",
        "target": configs.ODE_TARGET,
        "ihid": instrument_set.ihid,
        "iid": instrument_set.iid,
        "pt": instrument_set.pt,
        "featurename": feature.name,
        "loc": loc,
    }
    if min_obs_time:
        params["minobtime"] = min_obs_time
    if max_obs_time:
        params["maxobtime"] = max_obs_time
    return params


def count(
    client: ODEClient,
    feature: Feature,
    instrument_set: InstrumentSet,
    *,
    loc: str = configs.DEFAULT_LOC,
    min_obs_time: str | None = None,
    max_obs_time: str | None = None,
) -> int:
    """Return how many products match a feature and instrument set.

    Args:
        client: The ODE client to query with.
        feature: The feature whose name sets the query bounding box.
        instrument_set: The instrument host, instrument, and product type.
        loc: The ODE containment mode, "o" for strict containment.
        min_obs_time: Optional minimum UTC observation time.
        max_obs_time: Optional maximum UTC observation time.

    Returns:
        The product count.
    """
    params = _base_params(feature, instrument_set, loc, min_obs_time, max_obs_time)
    params["results"] = "c"
    results = client.query(params)
    return int(results.get("Count", 0))


def fetch_products(
    client: ODEClient,
    feature: Feature,
    instrument_set: InstrumentSet,
    *,
    loc: str = configs.DEFAULT_LOC,
    total: int | None = None,
    min_obs_time: str | None = None,
    max_obs_time: str | None = None,
) -> list[ProductRecord]:
    """Fetch all product metadata for a feature and instrument set.

    Each record keeps the retained ODE fields plus provenance describing the
    feature, its bounding box, and when the record was retrieved. Coordinates
    are stored exactly as ODE returns them, in degrees.

    ODE offset paging is only stable when a sort order is given, so a fixed
    order is requested and records are deduplicated by product id and gathered
    until the authoritative count is reached. This tolerates the occasional
    duplicate ODE returns at a page boundary.

    Args:
        client: The ODE client to query with.
        feature: The feature whose name sets the query bounding box.
        instrument_set: The instrument host, instrument, and product type.
        loc: The ODE containment mode, "o" for strict containment.
        total: The known product count, fetched if not given.
        min_obs_time: Optional minimum UTC observation time.
        max_obs_time: Optional maximum UTC observation time.

    Returns:
        One deduplicated record per product.
    """
    if total is None:
        total = count(
            client,
            feature,
            instrument_set,
            loc=loc,
            min_obs_time=min_obs_time,
            max_obs_time=max_obs_time,
        )
    if total == 0:
        return []
    provenance = {
        "feature_name": feature.name,
        "feature_class": feature.feature_class,
        "feature_min_lat": feature.min_lat,
        "feature_max_lat": feature.max_lat,
        "feature_west_lon": feature.west_lon,
        "feature_east_lon": feature.east_lon,
        "loc_mode": loc,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    records: list[ProductRecord] = []
    seen: set[str] = set()
    offset = 0
    while len(seen) < total:
        params = _base_params(feature, instrument_set, loc, min_obs_time, max_obs_time)
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
            record = {
                field: item[field] for field in configs.RETAINED_FIELDS if field in item
            }
            record.update(provenance)
            records.append(record)
            added += 1
        if added == 0:
            break
        offset += len(items)
    return records

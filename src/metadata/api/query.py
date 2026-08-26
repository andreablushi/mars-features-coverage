"""Product metadata queries for one feature and instrument set."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, TypeAlias

import utils.disk.provenance as provenance
from metadata import configs
from metadata.api.client import ODEClient
from metadata.api.response import as_items
from metadata.models.errors import ODEError
from models.feature import Feature
from models.instrument import InstrumentSet

Box = tuple[float, float, float, float]
ProductRecord: TypeAlias = dict[str, Any]


def query_boxes(feature: Feature) -> tuple[Box, ...]:
    """Return the lat/lon boxes a feature has to be asked for in.

    Args:
        feature: The feature to query.

    Returns:
        One box as (min_lat, max_lat, west_lon, east_lon), or two around a pole.
    """
    if feature.circles_a_pole:
        return tuple(
            (feature.min_lat, feature.max_lat, west, east)
            for west, east in configs.LONGITUDE_HALVES
        )
    return ((feature.min_lat, feature.max_lat, feature.west_lon, feature.east_lon),)


def _base_params(box: Box, instrument_set: InstrumentSet, loc: str) -> dict[str, str]:
    """Build the shared product query parameters for one box and set.

    Args:
        box: The lat/lon box to ask for.
        instrument_set: The instrument host, instrument, and product type.
        loc: "f" for every footprint overlapping the box, "o" for only those inside.

    Returns:
        The parameter dictionary without a results selector.
    """
    min_lat, max_lat, west_lon, east_lon = box
    params = {
        "query": "product",
        "target": configs.ODE_TARGET,
        "ihid": instrument_set.ihid,
        "iid": instrument_set.iid,
        "pt": instrument_set.pt,
        "minlat": str(min_lat),
        "maxlat": str(max_lat),
        "westernlon": str(west_lon),
        "easternlon": str(east_lon),
        "loc": loc,
    }
    if instrument_set.product_id:
        params["productid"] = instrument_set.product_id
    return params


def _pages(client: ODEClient, params: dict[str, str]) -> Iterator[list[Any]]:
    """Count one box's products, then walk them a page at a time.

    Args:
        client: The ODE client to query with.
        params: The box and instrument parameters to page through.

    Yields:
        Each page's raw product items, until they run out.

    Raises:
        ODEError: When ODE reports no usable count.
    """
    raw = client.query({**params, "results": "c"}).get("Count")
    try:
        total = int(raw)
    except (TypeError, ValueError):
        raise ODEError(f"ODE returned no product count, found {raw!r}") from None
    if total < 0:
        raise ODEError(f"ODE could not place the query and returned a count of {total}")

    offset = 0
    while offset < total:
        page = client.query(
            {
                **params,
                "results": "opm",
                "order": configs.PAGE_ORDER,
                "limit": str(configs.PAGE_SIZE),
                "offset": str(offset),
            }
        )
        items = as_items(page, "Products", "Product")
        if not items:
            return
        yield items
        offset += len(items)


def _identity(item: dict[str, Any]) -> tuple[str, str]:
    """Return what makes one stored record distinct from another.

    Args:
        item: One raw product object from an ODE response.

    Returns:
        The footprint and acquisition time, empty when ODE published no footprint.
    """
    footprint = str(item.get("Footprint_C0_geometry") or "")
    if not footprint:
        return ("", str(item.get("pdsid") or item.get("ode_id")))
    return (footprint, str(item.get("UTC_start_time") or ""))


def fetch_products(
    client: ODEClient,
    feature: Feature,
    instrument_set: InstrumentSet,
    loc: str,
) -> list[ProductRecord]:
    """Fetch all product metadata for a feature and instrument set.

    Args:
        client: The ODE client to query with.
        feature: The feature whose box the query is built from.
        instrument_set: The instrument host, instrument, and product type.
        loc: Which products the box returns, recorded with each one.

    Returns:
        One record per distinct product, in the order ODE returned them.
    """
    stamped = provenance.stamp(feature, instrument_set, loc)
    records: list[ProductRecord] = []
    seen: set[tuple[str, str]] = set()
    for box in query_boxes(feature):
        for items in _pages(client, _base_params(box, instrument_set, loc)):
            for item in items:
                identity = _identity(item)
                if identity in seen:
                    continue
                seen.add(identity)
                kept = {f: item[f] for f in configs.RETAINED_FIELDS if f in item}
                records.append(kept | stamped)
    return records

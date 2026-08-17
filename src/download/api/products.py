"""Product metadata queries for one feature and instrument set."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, TypeAlias

from download import configs
from download.api.client import ODEClient, ODEError, as_items
from download.selection.fields import retain_fields
from models.feature import Feature
from models.instrument import InstrumentSet

Box = tuple[float, float, float, float]
ProductRecord: TypeAlias = dict[str, Any]


def query_boxes(feature: Feature) -> tuple[Box, ...]:
    """Return the lat/lon boxes a feature has to be asked for in.

    The box is given explicitly rather than by feature name so the pipeline
    measures coverage against the same ground it queried, and so a box ODE
    cannot handle can be reshaped here instead of failing silently there. A
    feature running through every longitude is asked for in two halves, since
    its west and east longitudes are equal and a box from a longitude back to
    itself encloses nothing.

    Args:
        feature: The feature to query.

    Returns:
        One box as (min_lat, max_lat, west_lon, east_lon), or two for a feature
        that circles a pole.
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
        loc: Which products the box returns, "f" for every footprint that
            overlaps it and "o" for only those falling entirely inside.

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


def _count(client: ODEClient, params: dict[str, str]) -> int:
    """Return how many products one box holds, refusing an unusable answer.

    ODE reports a query it cannot place, such as one whose box has no width,
    with a Success status and a count of -1. Read as a number that is fewer
    products than none, which paging quietly satisfies by fetching nothing and
    writing an empty file that every later run then skips. It is a failure, so
    it is raised as one.

    Args:
        client: The ODE client to query with.
        params: The box and instrument parameters to count.

    Returns:
        The product count.

    Raises:
        ODEError: When ODE reports no usable count.
    """
    results = client.query({**params, "results": "c"})
    raw = results.get("Count")
    try:
        total = int(raw)
    except (TypeError, ValueError):
        raise ODEError(f"ODE returned no product count, found {raw!r}") from None
    if total < 0:
        raise ODEError(f"ODE could not place the query and returned a count of {total}")
    return total


def _pages(
    client: ODEClient, params: dict[str, str], total: int
) -> Iterator[list[Any]]:
    """Walk one box's products a page at a time.

    Paging runs to the count ODE gave rather than stopping at the first page
    that adds nothing new, because a page landing entirely on products already
    seen is what a boundary between two pages looks like, not the end of the
    result set.

    Args:
        client: The ODE client to query with.
        params: The box and instrument parameters to page through.
        total: How many products the box holds.

    Yields:
        Each page's raw product items, until they run out.
    """
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

    ODE publishes one record per archived file rather than per observation, so
    a single CRISM acquisition arrives once per detector and processing level:
    201 survey files over Gale describe 49 distinct patches of ground. A record
    repeating both the footprint and the acquisition time of one already kept
    covers nothing the first did not, exactly rather than to within rounding,
    so it is dropped.

    Keying on the ground rather than on the observation is what keeps the pairs
    that only look alike: HiRISE files its red and colour products under one
    acquisition time, and the colour strip is the narrower of the two, so
    collapsing by time would throw away a footprint and keep whichever came
    first. A record with no footprint has no ground to compare and falls back
    to its own id, so the count of what could not be used stays honest.

    Args:
        item: One raw product object from an ODE response.

    Returns:
        The footprint and acquisition time, or an empty footprint and the
        product id when ODE published no footprint.
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

    Each record keeps the retained ODE fields plus provenance describing the
    feature, its bounding box, and when the record was retrieved. Coordinates
    are stored exactly as ODE returns them, in degrees.

    ODE offset paging is only stable when a sort order is given, so a fixed
    order is requested and records are deduplicated while paging rather than
    through selection.dedupe, so a large feature never holds every raw page in
    memory at once.

    Args:
        client: The ODE client to query with.
        feature: The feature whose box the query is built from.
        instrument_set: The instrument host, instrument, and product type.
        loc: Which products the box returns, recorded with each one.

    Returns:
        One record per distinct product, in the order ODE returned them.
    """
    provenance = {
        "feature_name": feature.name,
        "feature_class": feature.feature_class,
        "feature_min_lat": feature.min_lat,
        "feature_max_lat": feature.max_lat,
        "feature_west_lon": feature.west_lon,
        "feature_east_lon": feature.east_lon,
        "instrument_set": instrument_set.key,
        "loc_mode": loc,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    records: list[ProductRecord] = []
    seen: set[tuple[str, str]] = set()
    for box in query_boxes(feature):
        params = _base_params(box, instrument_set, loc)
        for items in _pages(client, params, _count(client, params)):
            for item in items:
                identity = _identity(item)
                if identity in seen:
                    continue
                seen.add(identity)
                records.append(retain_fields(item) | provenance)
    return records

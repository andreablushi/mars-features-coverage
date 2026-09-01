"""Given a number, fetch the gridded tile it picks out from ODE into the cache."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from metadata.api.client import ODEClient
from preprocessing.fetching import catalogue
from preprocessing.fetching.products import bring
from preprocessing.mola import configs
from preprocessing.mola.loaders.utils import locations, naming

# The instrument host and instrument ODE publishes MOLA under.
IHID = "MGS"
IID = "MOLA"

# The ODE product type the gridded record is published under.
PRODUCT_TYPE = "MEGDR"

# ODE names a gridded product by its image file, suffix included.
ODE_SUFFIX = ".img"

# How many products to ask for at once. The whole record is under a hundred,
# so one page holds every tile of every resolution.
PAGE = 500


def available(
    resolution: int = configs.RESOLUTION, client: ODEClient | None = None
) -> list[str]:
    """Read the ids of every tile both planes are published for.

    The gridded record carries no per observation time, so the metadata stage
    does not fetch it and ODE is asked directly.

    Args:
        resolution: How fine a grid to keep, in pixels per degree.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The tile ids, sorted and without repeats.

    Raises:
        ValueError: When the resolution is not one MEGDR is published at.
    """
    if resolution not in naming.RESOLUTIONS.values():
        raise ValueError(f"MEGDR is not published at {resolution} pixels per degree.")
    owned = client or ODEClient()
    try:
        results = owned.query(
            {
                "query": "product",
                "results": "f",
                "target": "mars",
                "ihid": IHID,
                "iid": IID,
                "pt": PRODUCT_TYPE,
                "limit": str(PAGE),
            }
        )
    finally:
        if client is None:
            owned.close()

    found: dict[str, set[str]] = defaultdict(set)
    entries = results.get("Products", {})
    entries = entries.get("Product", []) if isinstance(entries, dict) else []
    for entry in entries if isinstance(entries, list) else [entries]:
        offers = entry.get("Product_files", {}).get("Product_file", [])
        for offer in offers if isinstance(offers, list) else [offers]:
            name = Path(str(offer.get("FileName", "")).lower())
            if name.suffix != ODE_SUFFIX:
                continue
            # Keep only wanted tiles, which drops the polar stereographic ones.
            tile = naming.parse(name.stem)
            if tile and naming.resolution(tile) == resolution:
                found[tile].add(name.stem)
    return sorted(
        tile
        for tile, seen in found.items()
        if seen.issuperset(naming.product(tile, kind) for kind in naming.KINDS)
    )


def sample(
    seed: int = 42,
    resolution: int = configs.RESOLUTION,
    client: ODEClient | None = None,
) -> Path:
    """Bring down the one tile a number picks out.

    Args:
        seed: The number to draw with.
        resolution: How fine a grid to draw from, in pixels per degree.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the topography label, whose image sits beside it.

    Raises:
        ValueError: When no tile is published at that resolution.
    """
    drawn = catalogue.pick(
        available(resolution, client),
        seed,
        f"MEGDR tile published at {resolution} pixels per degree",
    )
    return fetch(drawn, client)


def fetch(tile: str, client: ODEClient | None = None) -> Path:
    """Bring both planes of one tile down, or return what is here.

    Args:
        tile: The tile to fetch, such as 00n180hb.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the topography label, whose image sits beside it and whose
        counts plane sits in the same directory.

    Raises:
        FileNotFoundError: When ODE offers no download for a plane.
    """
    owned = client
    try:
        for kind in naming.KINDS:
            owned = bring(
                f"{naming.product(tile, kind)}{ODE_SUFFIX}",
                IHID,
                IID,
                PRODUCT_TYPE,
                locations.files(tile, kind),
                owned,
            )
    finally:
        if owned is not None and client is None:
            owned.close()
    return locations.label(tile)

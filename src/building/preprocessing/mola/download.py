"""Given a number, fetch the gridded tile it picks out from ODE into the cache."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from building.preprocessing.common import download
from building.preprocessing.common.disk import catalogue
from building.preprocessing.mola import configs

# What ODE publishes MOLA under.
ODE = {"ihid": "MGS", "iid": "MOLA"}

# The ODE product type the gridded record is published under.
PRODUCT_TYPE = "MEGDR"

# ODE names a gridded product by its image file, suffix included.
ODE_SUFFIX = ".img"

# How many products to ask for at once. The whole record is under a hundred,
# so one page holds every tile of every resolution.
PAGE = 500


def available(
    resolution: int = configs.RESOLUTION, client: download.Client | None = None
) -> list[str]:
    """Read the ids of every tile both planes are published for.

    The gridded record carries no per observation time, so the metadata stage
    does not fetch it and ODE is asked directly.

    Args:
        resolution: How fine a grid to keep, in pixels per degree.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The tile ids, sorted and without repeats.

    Raises:
        ValueError: When the resolution is not one MEGDR is published at.
    """
    if resolution not in configs.RESOLUTIONS.values():
        raise ValueError(f"MEGDR is not published at {resolution} pixels per degree.")
    with download.opened(client) as ode:
        entries = ode.query(pt=PRODUCT_TYPE, limit=str(PAGE), **ODE)
        names = {
            Path(filename).stem
            for entry in entries
            for filename in ode.published(entry)
            if filename.endswith(ODE_SUFFIX)
        }
    found: dict[str, set[str]] = defaultdict(set)
    for name in names:
        # Keep only wanted tiles, which drops the polar stereographic ones.
        tile = configs.NAMING.parse(name)
        if tile and configs.resolution(tile) == resolution:
            found[tile].add(name)
    return sorted(
        tile
        for tile, seen in found.items()
        if seen.issuperset(configs.NAMING.product(tile, kind) for kind in configs.KINDS)
    )


def sample(
    seed: int = 42,
    resolution: int = configs.RESOLUTION,
    client: download.Client | None = None,
) -> Path:
    """Bring down the one tile a number picks out.

    Args:
        seed: The number to draw with.
        resolution: How fine a grid to draw from, in pixels per degree.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to the topography label, whose image sits beside it.

    Raises:
        ValueError: When no tile is published at that resolution.
    """
    wanted = f"MEGDR tile published at {resolution} pixels per degree"
    return fetch(catalogue.sample(available(resolution, client), seed, wanted), client)


def fetch(tile: str, client: download.Client | None = None) -> Path:
    """Bring both planes of one tile down, or return what is here.

    Args:
        tile: The tile to fetch, such as 00n180hb.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to the topography label, whose image sits beside it and whose
        counts plane sits in the same directory.

    Raises:
        FileNotFoundError: When ODE offers no download for a plane.
    """
    with download.opened(client) as ode:
        for kind in configs.KINDS:
            product = configs.NAMING.product(tile, kind)
            ode.collect(
                f"{product}{ODE_SUFFIX}",
                configs.CACHE.files(tile, product, kind),
                pt=PRODUCT_TYPE,
                **ODE,
            )
    return configs.CACHE.files(tile, configs.NAMING.product(tile, configs.TOPOGRAPHY))[
        ".lbl"
    ]

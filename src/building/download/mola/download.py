"""Bringing down every MOLA gridded tile one feature's ground falls on."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from building.configs import mola as configs
from building.download.common import client as transport
from utils.ode import configs as ode_configs

if TYPE_CHECKING:
    from analysis.models.feature import Feature

# What ODE publishes MOLA under.
ODE = {"ihid": "MGS", "iid": "MOLA"}

# The ODE product type the gridded record is published under.
PRODUCT_TYPE = "MEGDR"

# ODE names a gridded product by its image file, suffix included.
ODE_SUFFIX = ".img"

# Which products a box returns: every tile whose footprint overlaps it, so a
# feature lying across an edge is answered with both the tiles it touches.
LOCATION = "f"

# How many products to ask for at once. The whole record is under a hundred, so
# one page holds every tile of every resolution.
PAGE = 500

# How fine a grid to read, in pixels per degree. MEGDR publishes 4, 16, 32, 64
# and 128, and only 128 is finer than a kilometre.
RESOLUTION = 128


def tiles(feature: Feature, client: transport.Client | None = None) -> list[str]:
    """Read which tiles hold one feature's ground.

    The gridded record carries no per observation time, so the selection never
    names a tile and ODE is asked which ones the feature's box falls on.

    Args:
        feature: The feature whose ground the tiles have to cover.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The tile ids both planes are published for, sorted and without repeats.
    """
    # A feature circling a pole is asked for in halves, since no single box
    # reaches round every longitude.
    spans = (
        ode_configs.LONGITUDE_HALVES
        if feature.circles_a_pole
        else ((feature.west_lon, feature.east_lon),)
    )
    names: set[str] = set()
    with transport.opened(client) as ode:
        for west, east in spans:
            entries = ode.query(
                pt=PRODUCT_TYPE,
                loc=LOCATION,
                limit=str(PAGE),
                minlat=str(feature.min_lat),
                maxlat=str(feature.max_lat),
                westernlon=str(west),
                easternlon=str(east),
                **ODE,
            )
            names.update(
                Path(filename).stem
                for entry in entries
                for filename in ode.published(entry)
                if filename.endswith(ODE_SUFFIX)
            )
    found: dict[str, set[str]] = defaultdict(set)
    for name in names:
        # Keep only wanted tiles, which drops the polar stereographic ones.
        tile = configs.NAMING.parse(name)
        if tile and configs.resolution(tile) == RESOLUTION:
            found[tile].add(name)
    return sorted(
        tile
        for tile, seen in found.items()
        if seen.issuperset(configs.NAMING.product(tile, kind) for kind in configs.KINDS)
    )


def fetch(tile: str, client: transport.Client | None = None) -> Path:
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
    wanted = {
        kind: configs.CACHE.files(tile, configs.NAMING.product(tile, kind), kind)
        for kind in configs.KINDS
    }
    if any(not path.exists() for files in wanted.values() for path in files.values()):
        with transport.opened(client) as ode:
            # ODE gives a gridded product no id of its own, so it is reached by
            # the name of the file it is published as and not by a product id.
            offered = {
                name: url
                for entry in ode.query(pt=PRODUCT_TYPE, limit=str(PAGE), **ODE)
                for name, url in ode.published(entry).items()
            }
            for kind, files in wanted.items():
                product = configs.NAMING.product(tile, kind)
                ode.bring(
                    files,
                    {
                        Path(name).suffix: url
                        for name, url in offered.items()
                        if Path(name).stem == product
                    },
                )
    return wanted[configs.TOPOGRAPHY][".lbl"]

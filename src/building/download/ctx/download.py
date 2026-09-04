"""Bringing one projected CTX scan down from ASU into the cache."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from building.configs import ctx as configs
from building.download.common import client as transport

# What ODE publishes CTX under.
ODE = {"ihid": "MRO", "iid": "CTX"}

# The only product type ODE carries for CTX, which is the raw scan. ASU builds
# the calibrated and projected one, and is asked for it directly.
PRODUCT_TYPE = "EDR"

# The suffix ODE names a raw scan by, whose URL says which volume it is on.
ODE_SUFFIX = ".img"

# The PDS volume a scan was archived on, which its download path runs through.
VOLUME = re.compile(r"/(?P<volume>mrox_\d+)/")

# Where ASU serves what it built, given the path the file sits at.
ASU_URL = "https://image.mars.asu.edu/stream/{name}?image={path}"

# Where ASU keeps one product of a scan, under the volume it was archived on.
ASU_PATH = "/mars/images/ctx/{volume}/{place}/{name}"

# Which ASU directory each kind is kept in, and what it is called there.
DIRECTORIES = {configs.IMAGE: "prj_full", configs.LABEL: "stage"}
REMOTE_SUFFIXES = {configs.IMAGE: ".tiff", configs.LABEL: ".scyl.isis.hdr"}

# How long to wait for the scan, which ASU builds on the way out.
TIMEOUT = 900.0


def observation_id(product_id: str) -> str | None:
    """Read which scan one product the selection kept belongs to.

    Args:
        product_id: The PDS product identifier, as the selection spells it.

    Returns:
        The scan to download, as ASU spells it, or None when the product is not
        one this instrument reads.

    """
    # ODE spells a scan in lower case, and ASU serves it in upper.
    scan = configs.NAMING.parse(product_id.lower())
    return scan.upper() if scan else None


def fetch(observation_id: str, client: transport.Client | None = None) -> Path:
    """Bring the projected scan and its label down, or return what is here.

    ASU keeps what it built under the volume the raw scan came from, and only
    ODE knows which that is.

    Args:
        observation_id: The observation to fetch.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to the scan's label, whose image sits beside it.

    Raises:
        FileNotFoundError: When ODE carries no raw scan to read the volume off.
        ValueError: When ODE offers that scan from no volume this can read.
    """
    destination = configs.CACHE.files(observation_id, observation_id)
    if any(not path.exists() for path in destination.values()):
        with transport.opened(client) as ode:
            offered = ode.offers(observation_id, pt=PRODUCT_TYPE, **ODE)
            if ODE_SUFFIX not in offered:
                raise FileNotFoundError(
                    f"ODE carries no raw scan for {observation_id}."
                )
            archived = VOLUME.search(offered[ODE_SUFFIX])
            if not archived:
                raise ValueError(f"{offered[ODE_SUFFIX]} names no CTX volume.")
            volume_id = archived["volume"]
            ode.bring(destination, _asu(observation_id, volume_id), TIMEOUT)
    return destination[configs.SUFFIXES[configs.LABEL]]


def _asu(observation_id: str, volume_id: str) -> dict[str, str]:
    """Return where ASU serves each product of one scan from.

    Args:
        observation_id: The scan to build the URLs for.
        volume_id: The PDS volume the raw scan was archived on, which is the
            directory ASU keeps what it built from it under.

    Returns:
        The URL each product is streamed from, keyed by its suffix on disk.
    """
    return {
        configs.SUFFIXES[kind]: ASU_URL.format(
            name=f"{observation_id}{configs.SUFFIXES[kind]}",
            path=quote(
                ASU_PATH.format(
                    volume=volume_id,
                    place=DIRECTORIES[kind],
                    name=f"{observation_id}{REMOTE_SUFFIXES[kind]}",
                )
            ),
        )
        for kind in configs.KINDS
    }

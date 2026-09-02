"""Given a number, fetch the projected scan it picks out from ASU into the cache."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from building.preprocessing.common import download
from building.preprocessing.common.disk import catalogue
from building.preprocessing.ctx import configs, locations, naming

# The metadata file each feature keeps its CTX products in.
EDR_METADATA_NAME = "mro_ctx_edr.jsonl"

# What ODE publishes CTX under.
ODE = {"ihid": "MRO", "iid": "CTX"}

# The only product type ODE carries for CTX, which is the raw scan. ASU builds
# the calibrated and projected one, and is asked for it directly.
PRODUCT_TYPE = "EDR"

# The suffix ODE names a raw scan by, whose URL says which volume it is on.
ODE_SUFFIX = ".img"

# Where ASU serves what it built, given the path the file sits at.
ASU_URL = "https://image.mars.asu.edu/stream/{name}?image={path}"


def available() -> list[str]:
    """Read the ids of every scan the metadata names.

    Returns:
        The observation ids, sorted and without repeats.
    """
    return catalogue.observations(
        configs.METADATA_ROOT, EDR_METADATA_NAME, naming.parse
    )


def sample(seed: int = 42, client: download.Client | None = None) -> Path:
    """Bring down the one scan a number picks out.

    Args:
        seed: The number to draw with.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to the scan's label, whose image sits beside it.

    Raises:
        ValueError: When the metadata holds no CTX products.
    """
    wanted = "CTX product in the metadata"
    return fetch(catalogue.sample(available(), seed, wanted), client)


def fetch(observation_id: str, client: download.Client | None = None) -> Path:
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
    destination = locations.files(observation_id)
    if any(not path.exists() for path in destination.values()):
        with download.opened(client) as ode:
            offered = ode.offers(observation_id, pt=PRODUCT_TYPE, **ODE)
        if ODE_SUFFIX not in offered:
            raise FileNotFoundError(f"ODE carries no raw scan for {observation_id}.")
        volume_id = naming.volume(offered[ODE_SUFFIX])
        download.bring(destination, _asu(observation_id, volume_id), configs.TIMEOUT)
    return locations.label(observation_id)


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
        naming.SUFFIXES[kind]: ASU_URL.format(
            name=f"{observation_id}{naming.SUFFIXES[kind]}",
            path=quote(naming.remote(observation_id, volume_id, kind)),
        )
        for kind in naming.KINDS
    }

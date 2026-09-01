"""Given a number, fetch the projected scan it picks out from ASU into the cache."""

from __future__ import annotations

import json
import random
from pathlib import Path
from urllib.parse import quote

from metadata.api.client import ODEClient
from preprocessing.ctx import configs
from preprocessing.ctx.loaders.utils import locations, naming
from preprocessing.fetching import ode
from preprocessing.fetching.download import stream

# The metadata file each feature keeps its CTX products in.
EDR_METADATA_NAME = "mro_ctx_edr.jsonl"

# The instrument host and instrument ODE publishes CTX under.
IHID = "MRO"
IID = "CTX"

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
    found = set()
    for source in configs.METADATA_ROOT.rglob(EDR_METADATA_NAME):
        # Read the metadata file line by line, which is a JSON object per line.
        for line in source.read_text().splitlines():
            if not line.strip():
                continue
            # The product id is in the `pdsid` field
            named = naming.parse(json.loads(line)["pdsid"])
            # Keep only wanted observations
            if named:
                found.add(named)
    return sorted(found)


def sample(seed: int = 42, client: ODEClient | None = None) -> Path:
    """Bring down the one scan a number picks out.

    Args:
        seed: The number to draw with.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the scan's label, whose image sits beside it.

    Raises:
        ValueError: When the metadata holds no CTX products.
    """
    pool = available()
    if not pool:
        raise ValueError("No CTX products found in the metadata.")
    return fetch(random.Random(seed).choice(pool), client)


def fetch(observation_id: str, client: ODEClient | None = None) -> Path:
    """Bring the projected scan and its label down, or return what is here.

    Args:
        observation_id: The observation to fetch.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the scan's label, whose image sits beside it.

    Raises:
        FileNotFoundError: When ODE carries no raw scan to read the volume off.
        ValueError: When ODE offers that scan from no volume this can read.
    """
    half = locations.files(observation_id)
    if all(path.exists() for path in half.values()):
        return locations.label(observation_id)

    volume_id = _volume(observation_id, client)
    for kind, path in half.items():
        if not path.exists():
            remote = naming.remote(observation_id, volume_id, kind)
            name = f"{observation_id}{naming.SUFFIXES[kind]}"
            url = ASU_URL.format(name=name, path=quote(remote))
            stream(url, path, configs.TIMEOUT)
    return locations.label(observation_id)


def _volume(observation_id: str, client: ODEClient | None) -> str:
    """Ask ODE which PDS volume one scan was archived on.

    ASU keeps what it built under the volume the raw scan came from, and only
    ODE knows which that is.

    Args:
        observation_id: The observation to ask about.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The volume, such as mrox_0009.

    Raises:
        FileNotFoundError: When ODE carries no raw scan for it.
        ValueError: When the URL it offers names no volume.
    """
    owned = client or ODEClient()
    try:
        offered = ode.product_files(
            observation_id, IHID, IID, PRODUCT_TYPE, (ODE_SUFFIX,), owned
        )
    finally:
        if client is None:
            owned.close()
    if ODE_SUFFIX not in offered:
        raise FileNotFoundError(f"ODE carries no raw scan for {observation_id}.")
    return naming.volume(offered[ODE_SUFFIX])

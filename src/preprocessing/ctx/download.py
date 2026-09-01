"""Given a number, fetch the projected scan it picks out from ASU into the cache."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from metadata.api.client import ODEClient
from preprocessing.common import catalogue
from preprocessing.common.download import Offers, borrowed, bring, published_on_ode
from preprocessing.ctx import configs, locations, naming

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
    return catalogue.observations(
        configs.METADATA_ROOT, EDR_METADATA_NAME, naming.parse
    )


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
    wanted = "CTX product in the metadata"
    return fetch(catalogue.pick(available(), seed, wanted), client)


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
    destination = locations.files(observation_id)
    if all(path.exists() for path in destination.values()):
        return locations.label(observation_id)
    with borrowed(client) as ode:
        volume_id = _volume(observation_id, ode)
    bring(observation_id, destination, _served_by_asu(volume_id), configs.TIMEOUT)
    return locations.label(observation_id)


def _served_by_asu(volume_id: str) -> Offers:
    """Return what answers where ASU serves a scan's projected products.

    Args:
        volume_id: The PDS volume the raw scan was archived on, which is the
            directory ASU keeps what it built from it under.

    Returns:
        Something that takes a scan id and the suffixes wanted, and gives back
        the URL ASU streams each one from.
    """

    def offers(observation_id: str, suffixes: tuple[str, ...]) -> dict[str, str]:
        """Build the URL ASU serves each wanted product of one scan from.

        Args:
            observation_id: The scan to build for.
            suffixes: Which file suffixes to keep.

        Returns:
            The URL for each of those suffixes.
        """
        built = {}
        for kind, suffix in naming.SUFFIXES.items():
            if suffix in suffixes:
                path = quote(naming.remote(observation_id, volume_id, kind))
                name = f"{observation_id}{suffix}"
                built[suffix] = ASU_URL.format(name=name, path=path)
        return built

    return offers


def _volume(observation_id: str, client: ODEClient) -> str:
    """Ask ODE which PDS volume one scan was archived on.

    ASU keeps what it built under the volume the raw scan came from, and only
    ODE knows which that is.

    Args:
        observation_id: The observation to ask about.
        client: The ODE client to ask through.

    Returns:
        The volume, such as mrox_0009.

    Raises:
        FileNotFoundError: When ODE carries no raw scan for it.
        ValueError: When the URL it offers names no volume.
    """
    offers = published_on_ode(IHID, IID, PRODUCT_TYPE, client)
    offered = offers(observation_id, (ODE_SUFFIX,))
    if ODE_SUFFIX not in offered:
        raise FileNotFoundError(f"ODE carries no raw scan for {observation_id}.")
    return naming.volume(offered[ODE_SUFFIX])

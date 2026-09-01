"""Given a number, fetch the radargram it picks out from ODE into the cache."""

from __future__ import annotations

from pathlib import Path

from metadata.api.client import ODEClient
from preprocessing.fetching import catalogue
from preprocessing.fetching.products import bring
from preprocessing.sharad import configs
from preprocessing.sharad.loaders.utils import locations, naming

# The metadata file each feature keeps its radargram products in.
RDR_METADATA_NAME = "mro_sharad_usrdrv2.jsonl"

# The instrument host and instrument ODE publishes SHARAD under.
IHID = "MRO"
IID = "SHARAD"

# The ODE product types a radargram and its geometry are published under.
TYPES = {naming.OBSERVATION: "USRDRV2", naming.GEOMETRY: "USGEOMV2"}


def available() -> list[str]:
    """Read the ids of every radargram the metadata names.

    Returns:
        The observation ids, sorted and without repeats.
    """
    found = set()
    for product_id in catalogue.product_ids(configs.METADATA_ROOT, RDR_METADATA_NAME):
        named = naming.parse(product_id.lower())
        # Keep only wanted observations
        if named:
            found.add(named)
    return sorted(found)


def sample(seed: int = 42, client: ODEClient | None = None) -> Path:
    """Bring down the one radargram a number picks out.

    Args:
        seed: The number to draw with.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the radargram's label, whose image sits beside it.

    Raises:
        ValueError: When the metadata holds no radargram products.
    """
    drawn = catalogue.pick(available(), seed, "radargram in the metadata")
    return fetch(drawn, client)


def fetch(observation_id: str, client: ODEClient | None = None) -> Path:
    """Bring one radargram and its geometry down, or return what is here.

    Args:
        observation_id: The observation to fetch.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the radargram's label, whose image sits beside it and whose
        geometry sits in the `geom` subdirectory.

    Raises:
        FileNotFoundError: When ODE offers no download for a product.
    """
    owned = client
    try:
        for kind, product_type in TYPES.items():
            owned = bring(
                naming.product(observation_id, kind),
                IHID,
                IID,
                product_type,
                locations.files(observation_id, kind),
                owned,
            )
    finally:
        if owned is not None and client is None:
            owned.close()
    return locations.label(observation_id)

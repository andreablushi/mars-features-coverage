"""Given a number, fetch the radargram it picks out from ODE into the cache."""

from __future__ import annotations

from pathlib import Path

from metadata.api.client import ODEClient
from preprocessing.common import catalogue
from preprocessing.common.download import borrowed, bring, published_on_ode
from preprocessing.sharad import configs, locations, naming

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
    return catalogue.observations(
        configs.METADATA_ROOT, RDR_METADATA_NAME, lambda p: naming.parse(p.lower())
    )


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
    return fetch(catalogue.pick(available(), seed, "radargram in the metadata"), client)


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
    with borrowed(client) as ode:
        for kind, product_type in TYPES.items():
            bring(
                naming.product(observation_id, kind),
                locations.files(observation_id, kind),
                published_on_ode(IHID, IID, product_type, ode),
            )
    return locations.label(observation_id)

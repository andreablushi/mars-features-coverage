"""Given a number, fetch the radargram it picks out from ODE into the cache."""

from __future__ import annotations

from pathlib import Path

from building.preprocessing.common import download
from building.preprocessing.common.disk import catalogue
from building.preprocessing.sharad import configs, locations, naming

# The metadata file each feature keeps its radargram products in.
RDR_METADATA_NAME = "mro_sharad_usrdrv2.jsonl"

# What ODE publishes SHARAD under.
ODE = {"ihid": "MRO", "iid": "SHARAD"}

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


def sample(seed: int = 42, client: download.Client | None = None) -> Path:
    """Bring down the one radargram a number picks out.

    Args:
        seed: The number to draw with.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to the radargram's label, whose image sits beside it.

    Raises:
        ValueError: When the metadata holds no radargram products.
    """
    wanted = "radargram in the metadata"
    return fetch(catalogue.sample(available(), seed, wanted), client)


def fetch(observation_id: str, client: download.Client | None = None) -> Path:
    """Bring one radargram and its geometry down, or return what is here.

    Args:
        observation_id: The observation to fetch.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to the radargram's label, whose image sits beside it and whose
        geometry sits in the `geom` subdirectory.

    Raises:
        FileNotFoundError: When ODE offers no download for a product.
    """
    with download.opened(client) as ode:
        for kind, product_type in TYPES.items():
            ode.collect(
                naming.product(observation_id, kind),
                locations.files(observation_id, kind),
                pt=product_type,
                **ODE,
            )
    return locations.label(observation_id)

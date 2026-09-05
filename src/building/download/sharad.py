"""Bringing one SHARAD radargram down from ODE into the cache."""

from __future__ import annotations

from pathlib import Path

import httpx

from building.configs import sharad as configs
from building.download import archive

# What ODE publishes SHARAD under.
ODE = {"ihid": "MRO", "iid": "SHARAD"}

# The ODE product types a radargram and its geometry are published under.
TYPES = {configs.OBSERVATION: "USRDRV2", configs.GEOMETRY: "USGEOMV2"}


def observation_id(product_id: str) -> str | None:
    """Read which observation one product the selection kept belongs to.

    Args:
        product_id: The PDS product identifier, as the selection spells it.

    Returns:
        The observation to download, or None when the product is not one this
        instrument reads.
    """
    return configs.NAMING.parse(product_id.lower())


def fetch(observation_id: str, client: httpx.Client) -> Path:
    """Bring one radargram and its geometry down, or return what is here.

    Args:
        observation_id: The observation to fetch.
        client: The client whose connections every query is asked over.

    Returns:
        The path to the radargram's label, whose image sits beside it and whose
        geometry sits in the `geom` subdirectory.

    Raises:
        FileNotFoundError: When ODE offers no download for a product.
    """
    for kind, product_type in TYPES.items():
        product_id = configs.NAMING.product(observation_id, kind)
        archive.collect(
            client,
            product_id,
            configs.CACHE.files(observation_id, product_id, kind),
            pt=product_type,
            **ODE,
        )
    return configs.CACHE.files(
        observation_id,
        configs.NAMING.product(observation_id, configs.OBSERVATION),
        configs.OBSERVATION,
    )[".lbl"]

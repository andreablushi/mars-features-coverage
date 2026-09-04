"""Bringing one CRISM observation down from ODE into the cache."""

from __future__ import annotations

from pathlib import Path

from building.common.pds import labels
from building.configs import crism as configs
from building.download.common import client as transport

# What ODE publishes CRISM under.
ODE = {"ihid": "MRO", "iid": "CRISM"}

# The ODE product types an observation and its geometry are published under.
TYPES = {configs.OBSERVATION: "TRDR", configs.GEOMETRY: "DDR"}

# The ODE product type a wavelength file is published under.
WAVELENGTH_TYPE = "CDR"


def observation_id(product_id: str) -> str | None:
    """Read which observation one product the selection kept belongs to.

    Args:
        product_id: The PDS product identifier, as the selection spells it.

    Returns:
        The observation to download, or None when the product names no detector
        of its own and so is not one both detectors can be fetched from.
    """
    product_id = product_id.lower()
    parts = configs.NAMING.parts(product_id)
    # Keep only wanted products, which name a detector of their own.
    return configs.NAMING.parse(product_id) if parts and parts["detector"] else None


def fetch(
    observation_id: str, client: transport.Client | None = None
) -> dict[str, Path]:
    """Bring both detectors of one observation down, or return what is here.

    Args:
        observation_id: The observation to fetch.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to each detector's label, whose image sits beside it and whose
        geometry sits in the `ddr` subdirectory.

    Raises:
        FileNotFoundError: When ODE offers no download for a product.
        KeyError: When a label names no wavelength file.
    """
    with transport.opened(client) as ode:
        for detector in configs.DETECTORS:
            for kind, product_type in TYPES.items():
                product_id = configs.NAMING.product(
                    observation_id, kind, detector=detector
                )
                ode.collect(
                    product_id,
                    configs.CACHE.files(observation_id, product_id, kind),
                    pt=product_type,
                    **ODE,
                )
        found = {
            detector: configs.CACHE.files(
                observation_id,
                configs.NAMING.product(
                    observation_id, configs.OBSERVATION, detector=detector
                ),
            )[".lbl"]
            for detector in configs.DETECTORS
        }
        # Only now do the labels exist to be asked which file calibrated them.
        for label in found.values():
            name = Path(labels.load(label)[configs.WAVELENGTH_KEY]).stem
            ode.collect(
                name,
                configs.CACHE.files(configs.WAVELENGTH_DIR, name.lower()),
                pt=WAVELENGTH_TYPE,
                **ODE,
            )
    return found

"""Given a number, fetch the observation it picks out from ODE into the cache."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from metadata.api.client import ODEClient
from preprocessing.common import catalogue
from preprocessing.common.download import borrowed, bring, published_on_ode
from preprocessing.common.pds import labels
from preprocessing.crism import configs, locations, naming

# The metadata file each feature keeps its multispectral survey products in.
MSP_METADATA_NAME = "mro_crism_trdr_msp.jsonl"

# The instrument host and instrument ODE publishes CRISM under.
IHID = "MRO"
IID = "CRISM"

# The ODE product types an observation and its geometry are published under.
TYPES = {naming.OBSERVATION: "TRDR", naming.GEOMETRY: "DDR"}

# The ODE product type a wavelength file is published under.
WAVELENGTH_TYPE = "CDR"


def available() -> list[str]:
    """Read the ids of every observation both detectors were published for.

    Returns:
        The observation ids, sorted and without repeats.
    """
    found: dict[str, set[str]] = defaultdict(set)
    for product_id in catalogue.product_ids(configs.METADATA_ROOT, MSP_METADATA_NAME):
        # Keep only wanted observations, which name a detector of their own.
        if named := naming.parse(product_id.lower()):
            found[named[0]].add(named[1])
    return sorted(
        name for name, seen in found.items() if seen.issuperset(naming.DETECTORS)
    )


def sample(seed: int = 42, client: ODEClient | None = None) -> dict[str, Path]:
    """Bring down the one observation a number picks out.

    Args:
        seed: The number to draw with.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to each detector's label, keyed by detector.

    Raises:
        ValueError: When the metadata holds no multispectral survey products.
    """
    wanted = "multispectral survey product in the metadata"
    return fetch(catalogue.pick(available(), seed, wanted), client)


def fetch(observation_id: str, client: ODEClient | None = None) -> dict[str, Path]:
    """Bring both detectors of one observation down, or return what is here.

    Args:
        observation_id: The observation to fetch.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to each detector's label, whose image sits beside it and whose
        geometry sits in the `ddr` subdirectory.

    Raises:
        FileNotFoundError: When ODE offers no download for a product.
        KeyError: When a label names no wavelength file.
    """
    with borrowed(client) as ode:
        for detector in naming.DETECTORS:
            for kind, product_type in TYPES.items():
                bring(
                    naming.product(observation_id, detector, kind),
                    locations.files(observation_id, detector, kind),
                    published_on_ode(IHID, IID, product_type, ode),
                )
        # Only now do the labels exist to be asked which file calibrated them.
        offers = published_on_ode(IHID, IID, WAVELENGTH_TYPE, ode)
        for label in locations.labels(observation_id).values():
            name = naming.wavelength(labels.load(label))
            bring(name, locations.wavelength_file(name), offers)
    return locations.labels(observation_id)


def wavelength_file(name: str, client: ODEClient | None = None) -> Path:
    """Bring down the wavelength file one label names, or return what is here.

    Args:
        name: The product id ODE knows the wavelength file by.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the file's image, whose label sits beside it.

    Raises:
        FileNotFoundError: When ODE offers no download for it.
    """
    half = locations.wavelength_file(name)
    with borrowed(client) as ode:
        bring(name, half, published_on_ode(IHID, IID, WAVELENGTH_TYPE, ode))
    return half[".img"]

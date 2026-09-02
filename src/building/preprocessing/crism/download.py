"""Given a number, fetch the observation it picks out from ODE into the cache."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from building.preprocessing.common import download
from building.preprocessing.common.disk import catalogue
from building.preprocessing.common.pds import labels
from building.preprocessing.crism import configs

# The metadata file each feature keeps its multispectral survey products in.
MSP_METADATA_NAME = "mro_crism_trdr_msp.jsonl"

# What ODE publishes CRISM under.
ODE = {"ihid": "MRO", "iid": "CRISM"}

# The ODE product types an observation and its geometry are published under.
TYPES = {configs.OBSERVATION: "TRDR", configs.GEOMETRY: "DDR"}

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
        parts = configs.NAMING.parts(product_id.lower())
        if parts and parts["detector"]:
            found[configs.NAMING.parse(product_id.lower())].add(parts["detector"])
    return sorted(
        name for name, seen in found.items() if seen.issuperset(configs.DETECTORS)
    )


def sample(seed: int = 42, client: download.Client | None = None) -> dict[str, Path]:
    """Bring down the one observation a number picks out.

    Args:
        seed: The number to draw with.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to each detector's label, keyed by detector.

    Raises:
        ValueError: When the metadata holds no multispectral survey products.
    """
    wanted = "multispectral survey product in the metadata"
    return fetch(catalogue.sample(available(), seed, wanted), client)


def fetch(
    observation_id: str, client: download.Client | None = None
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
    with download.opened(client) as ode:
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


def wavelength_file(name: str, client: download.Client | None = None) -> Path:
    """Bring down the wavelength file one label names, or return what is here.

    Args:
        name: The product id ODE knows the wavelength file by.
        client: A client to reuse, or None to open one for this call.

    Returns:
        The path to the file's image, whose label sits beside it.

    Raises:
        FileNotFoundError: When ODE offers no download for it.
    """
    half = configs.CACHE.files(configs.WAVELENGTH_DIR, name.lower())
    with download.opened(client) as ode:
        ode.collect(name, half, pt=WAVELENGTH_TYPE, **ODE)
    return half[".img"]

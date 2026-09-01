"""Given a number, fetch the observation it picks out from ODE into the cache."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from metadata.api.client import ODEClient
from preprocessing.crism import configs
from preprocessing.crism.loaders.utils import locations, naming
from preprocessing.fetching.products import bring
from preprocessing.pds import labels

# The metadata file each feature keeps its multispectral survey products in.
MSP_METADATA_NAME = "mro_crism_trdr_msp.jsonl"

# The instrument host and instrument ODE publishes CRISM under.
IHID = "MRO"
IID = "CRISM"

# The ODE product types an observation and its geometry are published under.
OBSERVATION_TYPE = "TRDR"
GEOMETRY_TYPE = "DDR"

# The ODE product type a wavelength file is published under.
WAVELENGTH_TYPE = "CDR"


def available() -> list[str]:
    """Read the ids of every observation both detectors were published for.

    Returns:
        The observation ids, sorted and without repeats.
    """
    found: dict[str, set[str]] = defaultdict(set)
    for source in configs.METADATA_ROOT.rglob(MSP_METADATA_NAME):
        # Read the metadata file line by line, which is a JSON object per line.
        for line in source.read_text().splitlines():
            if not line.strip():
                continue
            # The product id is in the `pdsid` field
            named = naming.parse(json.loads(line)["pdsid"].lower())
            # Keep only wanted observations
            if named:
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
    pool = available()
    if not pool:
        raise ValueError("No multispectral survey products found in the metadata.")
    return fetch(random.Random(seed).choice(pool), client)


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
    wanted = {
        naming.product(observation_id, detector): (
            OBSERVATION_TYPE,
            locations.files(observation_id, detector),
        )
        for detector in naming.DETECTORS
    } | {
        naming.product(observation_id, detector, naming.GEOMETRY): (
            GEOMETRY_TYPE,
            locations.files(observation_id, detector, naming.GEOMETRY),
        )
        for detector in naming.DETECTORS
    }

    owned = client
    try:
        for product_id, (product_type, half) in wanted.items():
            owned = bring(product_id, IHID, IID, product_type, half, owned)
        # Only now do the labels exist to be asked which file calibrated them.
        for label in locations.labels(observation_id).values():
            name = naming.wavelength(labels.load(label))
            owned = bring(
                name,
                IHID,
                IID,
                WAVELENGTH_TYPE,
                locations.wavelength_file(name),
                owned,
            )
    finally:
        if owned is not None and client is None:
            owned.close()
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
    owned = bring(name, IHID, IID, WAVELENGTH_TYPE, half, client)
    if owned is not None and client is None:
        owned.close()
    return half[".img"]

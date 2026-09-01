"""Given a number, fetch the observation it picks out from ODE into the cache."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

import httpx

from metadata.api.client import ODEClient
from preprocessing.crism import configs
from preprocessing.crism.loaders.utils import locations, naming, pds
from utils.disk.files import atomic_path

# The metadata file each feature keeps its multispectral survey products in.
MSP_METADATA_NAME = "mro_crism_trdr_msp.jsonl"

# How long to wait for the larger half of a product.
TIMEOUT = 300.0

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
            owned = _bring(product_id, product_type, half, owned)
        # Only now do the labels exist to be asked which file calibrated them.
        for label in locations.labels(observation_id).values():
            name = naming.wavelength(pds.load_label(label))
            owned = _bring(
                name, WAVELENGTH_TYPE, locations.wavelength_file(name), owned
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
    owned = _bring(name, WAVELENGTH_TYPE, half, client)
    if owned is not None and client is None:
        owned.close()
    return half[".img"]


def _bring(
    product_id: str,
    product_type: str,
    half: dict[str, Path],
    client: ODEClient | None,
) -> ODEClient | None:
    """Download whichever halves of one product are not here yet.

    Args:
        product_id: The product to fetch.
        product_type: The ODE product type it is published under.
        half: Where each of its halves belongs, keyed by suffix.
        client: An ODE client to use, or None to open one if anything is needed.

    Returns:
        The client used, which is the one given when nothing had to be fetched.

    Raises:
        FileNotFoundError: When ODE offers no download for a half.
    """
    if all(path.exists() for path in half.values()):
        return client
    owned = client or ODEClient()
    offered = _build_urls(product_id, owned, product_type)
    missing = [s for s in locations.SUFFIXES if not offered.get(s)]
    if missing:
        raise FileNotFoundError(f"ODE offers no {', '.join(missing)} for {product_id}.")
    for suffix, path in half.items():
        if not path.exists():
            _download(offered[suffix], path)
    return owned


def _build_urls(
    product_id: str, client: ODEClient, product_type: str
) -> dict[str, str]:
    """Ask ODE where the halves of one product can be downloaded.

    Args:
        product_id: The product, such as msp000396ba_01_if214l_trr3.
        client: The ODE client to ask through.
        product_type: The ODE product type it is published under.

    Returns:
        The download URL for each suffix the product offers, keyed by suffix.
    """
    results = client.query(
        {
            "query": "product",
            "results": "f",
            "target": "mars",
            "ihid": "MRO",
            "iid": "CRISM",
            "pt": product_type,
            "productid": product_id,
        }
    )
    found = {}
    entry = results.get("Products", {}).get("Product", {})
    offers = entry.get("Product_files", {}).get("Product_file", [])
    for offer in offers if isinstance(offers, list) else [offers]:
        suffix = Path(str(offer.get("FileName", "")).lower()).suffix
        if offer.get("Type") == "Product" and suffix in locations.SUFFIXES:
            found[suffix] = str(offer.get("URL", ""))
    return found


def _download(url: str, path: Path) -> None:
    """Stream one file to disk, leaving nothing behind if it fails.

    Args:
        url: Where to read it from.
        path: Where it belongs once it is whole.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_path(path) as tmp, httpx.stream("GET", url, timeout=TIMEOUT) as reply:
        reply.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in reply.iter_bytes():
                handle.write(chunk)

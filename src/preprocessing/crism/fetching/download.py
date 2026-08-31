"""Picking observations the pipeline already selected, and bringing them down.

The ids come from the metadata already on disk, so the sanity check runs over
the same products the coverage stage chose rather than over the archive at
large. The metadata keeps no download URL, so ODE is asked for one per id.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import httpx

from metadata.api.client import ODEClient
from utils.disk import paths
from utils.disk.files import atomic_path

# The metadata file each feature keeps its multispectral survey products in.
MSP_METADATA_NAME = "mro_crism_trdr_msp.jsonl"

# What an id must carry to be an infrared I/F observation rather than its
# radiance twin or the visible detector beside it.
WANTED = ("_if", "l_trr")

# The two halves of a product, and how long to wait for the larger one.
SUFFIXES = (".lbl", ".img")
TIMEOUT = 300.0


def available(root: Path = paths.METADATA_ROOT) -> list[str]:
    """Read every multispectral survey observation the pipeline has selected.

    Args:
        root: The metadata root the coverage stage writes under.

    Returns:
        The product ids, in no particular order and without repeats.
    """
    found: set[str] = set()
    for source in root.rglob(MSP_METADATA_NAME):
        for line in source.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            product = str(json.loads(line).get("pdsid", "")).lower()
            if all(part in product for part in WANTED):
                found.add(product)
    return sorted(found)


def sample(count: int = 1, seed: int | None = None, **kwargs: Path) -> list[str]:
    """Pick observations at random from the ones already selected.

    Args:
        count: How many to pick.
        seed: Fixes the draw so a run can be repeated, or None to vary it.
        **kwargs: Passed to `available`, which takes the metadata root.

    Returns:
        The chosen product ids.

    Raises:
        ValueError: When the metadata holds no multispectral survey products.
    """
    pool = available(**kwargs)
    if not pool:
        raise ValueError("No multispectral survey products found in the metadata.")
    return random.Random(seed).sample(pool, min(count, len(pool)))


def urls(product_id: str, client: ODEClient) -> dict[str, str]:
    """Ask ODE where the halves of one observation can be downloaded.

    Args:
        product_id: The observation, such as msp000396ba_01_if214l_trr3.
        client: The ODE client to ask through.

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
            "pt": "TRDR",
            "productid": product_id,
        }
    )
    product = results.get("Products", {}).get("Product", {})
    files = product.get("Product_files", {}).get("Product_file", [])
    found = {}
    for entry in files if isinstance(files, list) else [files]:
        name = str(entry.get("FileName", "")).lower()
        suffix = Path(name).suffix
        if entry.get("Type") == "Product" and suffix in SUFFIXES:
            found[suffix] = str(entry.get("URL", ""))
    return found


def fetch(
    product_id: str,
    cache: Path = paths.CRISM_ROOT,
    client: ODEClient | None = None,
) -> Path:
    """Bring one observation down, or return it if it is already here.

    Args:
        product_id: The observation to fetch.
        cache: Where downloaded observations are kept.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the label, whose image sits beside it.

    Raises:
        FileNotFoundError: When ODE offers no download for the observation.
    """
    wanted = {suffix: cache / f"{product_id}{suffix}" for suffix in SUFFIXES}
    if all(path.exists() for path in wanted.values()):
        return wanted[".lbl"]

    owned = client or ODEClient()
    try:
        offered = urls(product_id, owned)
    finally:
        if client is None:
            owned.close()

    missing = [suffix for suffix in SUFFIXES if not offered.get(suffix)]
    if missing:
        raise FileNotFoundError(f"ODE offers no {', '.join(missing)} for {product_id}.")

    for suffix, path in wanted.items():
        if not path.exists():
            _download(offered[suffix], path)
    return wanted[".lbl"]


def fetch_label(
    product_id: str,
    cache: Path = paths.CRISM_ROOT,
    client: ODEClient | None = None,
) -> Path:
    """Bring down only the label of one observation, which is a few kilobytes.

    This is how the geometry of many observations can be compared without
    downloading any of their images.

    Args:
        product_id: The observation to fetch the label of.
        cache: Where downloaded observations are kept.
        client: An ODE client to reuse, or None to open one for this call.

    Returns:
        The path to the label.

    Raises:
        FileNotFoundError: When ODE offers no label for the observation.
    """
    path = cache / f"{product_id}.lbl"
    if path.exists():
        return path

    owned = client or ODEClient()
    try:
        offered = urls(product_id, owned)
    finally:
        if client is None:
            owned.close()

    if not offered.get(".lbl"):
        raise FileNotFoundError(f"ODE offers no label for {product_id}.")
    _download(offered[".lbl"], path)
    return path


def _download(url: str, path: Path) -> None:
    """Stream one file to disk, leaving nothing behind if it fails.

    Args:
        url: Where to read it from.
        path: Where it belongs once it is whole.

    Returns:
        None.
    """
    with atomic_path(path) as tmp, httpx.stream("GET", url, timeout=TIMEOUT) as reply:
        reply.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in reply.iter_bytes():
                handle.write(chunk)

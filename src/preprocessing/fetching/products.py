"""Bringing whichever halves of one product are not in the cache yet."""

from __future__ import annotations

from pathlib import Path

from metadata.api.client import ODEClient
from preprocessing.fetching import ode
from preprocessing.fetching.download import stream


def bring(
    product_id: str,
    ihid: str,
    iid: str,
    product_type: str,
    half: dict[str, Path],
    client: ODEClient | None,
) -> ODEClient | None:
    """Download whichever halves of one product are not here yet.

    Args:
        product_id: The product to fetch.
        ihid: The instrument host, such as MRO.
        iid: The instrument, such as CRISM.
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
    offered = ode.product_files(product_id, ihid, iid, product_type, tuple(half), owned)
    missing = [suffix for suffix in half if not offered.get(suffix)]
    if missing:
        raise FileNotFoundError(f"ODE offers no {', '.join(missing)} for {product_id}.")
    for suffix, path in half.items():
        if not path.exists():
            stream(offered[suffix], path)
    return owned

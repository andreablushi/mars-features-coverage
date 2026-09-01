"""Finding where a product's files are published, and bringing them here."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from metadata.api.client import ODEClient
from utils.disk.files import atomic_path

# What answers where each half of one product can be downloaded from. It is
# given the product id and the suffixes wanted, and returns a URL per suffix.
Offers = Callable[[str, tuple[str, ...]], dict[str, str]]

# How long to wait for the larger half of a product.
TIMEOUT = 300.0


@contextmanager
def borrowed(client: ODEClient | None) -> Iterator[ODEClient]:
    """Yield a client to ask with, closing it only if it was opened here.

    Args:
        client: A client the caller is reusing, or None to open one.

    Yields:
        The client to ask through.
    """
    owned = client or ODEClient()
    try:
        yield owned
    finally:
        if client is None:
            owned.close()


def published_on_ode(
    ihid: str, iid: str, product_type: str, client: ODEClient
) -> Offers:
    """Return what answers where ODE publishes a product's files.

    Args:
        ihid: The instrument host, such as MRO.
        iid: The instrument, such as CRISM.
        product_type: The ODE product type the product is published under.
        client: The ODE client to ask through.

    Returns:
        Something that takes a product id and the suffixes wanted, and gives
        back the download URL of each suffix ODE offers.
    """

    def offers(product_id: str, suffixes: tuple[str, ...]) -> dict[str, str]:
        """Ask ODE where one product's files are.

        Args:
            product_id: The product to ask about.
            suffixes: Which file suffixes to keep.

        Returns:
            The download URL for each of those suffixes ODE offers.
        """
        results = client.query(
            {
                "query": "product",
                "results": "f",
                "target": "mars",
                "ihid": ihid,
                "iid": iid,
                "pt": product_type,
                "productid": product_id,
            }
        )
        return {
            suffix: url
            for suffix, url in _offered(results).items()
            if suffix in suffixes
        }

    return offers


def _offered(results: dict) -> dict[str, str]:
    """Read the download URL of every file one ODE answer names.

    Args:
        results: The parsed ODEResults of a product query.

    Returns:
        The URL of each file suffix the product is published as.
    """
    # ODE answers a query that matched nothing with a sentence, not a product.
    entry = results.get("Products", {})
    entry = entry.get("Product", {}) if isinstance(entry, dict) else {}
    entry = entry[0] if isinstance(entry, list) else entry
    files = entry.get("Product_files", {}).get("Product_file", [])
    found = {}
    for offer in files if isinstance(files, list) else [files]:
        suffix = Path(str(offer.get("FileName", "")).lower()).suffix
        if offer.get("Type") == "Product":
            found.setdefault(suffix, str(offer.get("URL", "")))
    return found


def bring(
    product_id: str,
    destination: dict[str, Path],
    offers: Offers,
    timeout: float = TIMEOUT,
) -> None:
    """Download whichever halves of one product are not on disk yet.

    Args:
        product_id: The product to fetch.
        destination: Where each of its halves belongs, keyed by suffix.
        offers: What answers where those halves can be downloaded from.
        timeout: How long to wait on each transfer.

    Returns:
        None.

    Raises:
        FileNotFoundError: When no download is offered for a half.
    """
    if all(path.exists() for path in destination.values()):
        return
    offered = offers(product_id, tuple(destination))
    missing = [suffix for suffix in destination if not offered.get(suffix)]
    if missing:
        raise FileNotFoundError(f"No {', '.join(missing)} offered for {product_id}.")
    for suffix, path in destination.items():
        if not path.exists():
            stream(offered[suffix], path, timeout)


def stream(url: str, path: Path, timeout: float = TIMEOUT) -> None:
    """Stream one file to disk, leaving nothing behind if it fails.

    Args:
        url: Where to read it from.
        path: Where it belongs once it is whole.
        timeout: How long to wait on the transfer.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_path(path) as tmp, httpx.stream("GET", url, timeout=timeout) as reply:
        reply.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in reply.iter_bytes():
                handle.write(chunk)

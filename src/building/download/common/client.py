"""The one client an archive is asked through, and what it brings down."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from utils.disk.files import atomic_path
from utils.ode.client import ODEClient

# How long to wait for the larger half of a product.
TIMEOUT = 300.0


class Client:
    """What an instrument asks where its products are, and downloads them from."""

    def __init__(self) -> None:
        """Open the client an archive is asked through.

        Returns:
            None.
        """
        self._ode = ODEClient()

    def query(self, **params: str) -> list[dict]:
        """Read the products one ODE query names, one entry each.

        Args:
            params: What to ask for, such as the instrument host, the
                instrument, the product type, and a product id or a page size.

        Returns:
            One entry per product ODE answers with, empty when it matched none.
        """
        results = self._ode.query(
            {"query": "product", "results": "f", "target": "mars", **params}
        )
        # ODE answers a query that matched nothing with a sentence, not a product.
        products = results.get("Products", {})
        entries = products.get("Product", []) if isinstance(products, dict) else []
        return entries if isinstance(entries, list) else [entries]

    def offers(self, product_id: str, **params: str) -> dict[str, str]:
        """Read where ODE offers each file of one product.

        Args:
            product_id: The product to ask about.
            params: What else names it, such as the instrument and its type.

        Returns:
            The download URL of each file suffix the product is published as,
            the first offer of a suffix winning.
        """
        entries = self.query(productid=product_id, **params)
        found: dict[str, str] = {}
        for name, url in self.published(entries[0] if entries else {}).items():
            found.setdefault(Path(name).suffix, url)
        return found

    def collect(
        self,
        product_id: str,
        destination: dict[str, Path],
        timeout: float = TIMEOUT,
        **params: str,
    ) -> None:
        """Download whichever halves of one ODE product are not on disk yet.

        Args:
            product_id: The product to fetch.
            destination: Where each of its halves belongs, keyed by suffix.
            timeout: How long to wait on each transfer.
            params: What names the product to ODE, such as the instrument host,
                the instrument and the product type.

        Returns:
            None.

        Raises:
            FileNotFoundError: When ODE offers no download for a missing half.
        """
        if any(not path.exists() for path in destination.values()):
            self.bring(destination, self.offers(product_id, **params), timeout)

    @staticmethod
    def published(entry: dict) -> dict[str, str]:
        """Read the name and URL of every file one ODE product entry offers.

        Args:
            entry: One product, as `query` returns it.

        Returns:
            The download URL of each file, keyed by its lowercase filename.
        """
        offered = entry.get("Product_files", {}).get("Product_file", [])
        return {
            str(offer.get("FileName", "")).lower(): str(offer.get("URL", ""))
            for offer in (offered if isinstance(offered, list) else [offered])
            if offer.get("Type") == "Product"
        }

    def bring(
        self,
        destination: dict[str, Path],
        urls: dict[str, str],
        timeout: float = TIMEOUT,
    ) -> None:
        """Stream whichever halves of one product are not on disk yet.

        Args:
            destination: Where each half belongs, keyed by suffix.
            urls: Where each half is served from, keyed by the same suffix.
            timeout: How long to wait on each transfer.

        Returns:
            None.

        Raises:
            FileNotFoundError: When a missing half is served from nowhere.
        """
        for suffix, path in destination.items():
            if path.exists():
                continue
            if not urls.get(suffix):
                raise FileNotFoundError(f"No {suffix} offered for {path.stem}.")
            self.stream(urls[suffix], path, timeout)

    @staticmethod
    def stream(url: str, path: Path, timeout: float = TIMEOUT) -> None:
        """Stream one file to disk, leaving nothing behind if it fails.

        Args:
            url: Where to read it from.
            path: Where it belongs once it is whole.
            timeout: How long to wait on the transfer.

        Returns:
            None.
        """
        with (
            atomic_path(path) as tmp,
            httpx.stream("GET", url, timeout=timeout) as reply,
        ):
            reply.raise_for_status()
            with tmp.open("wb") as handle:
                for chunk in reply.iter_bytes():
                    handle.write(chunk)

    def close(self) -> None:
        """Close the client.

        Returns:
            None.
        """
        self._ode.close()

    def __enter__(self) -> Client:
        """Return the client, so it can be opened in a with statement.

        Returns:
            The client itself.
        """
        return self

    def __exit__(self, *exception: object) -> None:
        """Close the client on the way out of a with statement.

        Args:
            exception: The exception being raised, which is not handled here.

        Returns:
            None.
        """
        self.close()


@contextmanager
def opened(client: Client | None) -> Iterator[Client]:
    """Yield a client to ask with, closing it only if it was opened here.

    Args:
        client: A client the caller is reusing, or None to open one.

    Yields:
        The client to ask through.
    """
    owned = client or Client()
    try:
        yield owned
    finally:
        if client is None:
            owned.close()

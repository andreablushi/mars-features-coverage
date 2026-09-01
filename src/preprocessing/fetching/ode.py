"""Asking ODE where the files of one product can be downloaded."""

from __future__ import annotations

from pathlib import Path

from metadata.api.client import ODEClient


def product_files(
    product_id: str,
    ihid: str,
    iid: str,
    product_type: str,
    suffixes: tuple[str, ...],
    client: ODEClient,
) -> dict[str, str]:
    """Ask ODE where the wanted halves of one product can be downloaded.

    Args:
        product_id: The product, such as msp000396ba_01_if214l_trr3.
        ihid: The instrument host, such as MRO.
        iid: The instrument, such as CRISM.
        product_type: The ODE product type it is published under.
        suffixes: Which file suffixes to keep, such as `.lbl` and `.img`.
        client: The ODE client to ask through.

    Returns:
        The download URL for each of those suffixes the product offers.
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
    found = {}
    # ODE answers a query that matched nothing with a sentence, not a product.
    entry = results.get("Products", {})
    entry = entry.get("Product", {}) if isinstance(entry, dict) else {}
    entry = entry[0] if isinstance(entry, list) else entry
    offers = entry.get("Product_files", {}).get("Product_file", [])
    for offer in offers if isinstance(offers, list) else [offers]:
        suffix = Path(str(offer.get("FileName", "")).lower()).suffix
        if offer.get("Type") == "Product" and suffix in suffixes:
            found[suffix] = str(offer.get("URL", ""))
    return found

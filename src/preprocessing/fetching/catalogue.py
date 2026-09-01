"""Reading the products the metadata stage wrote, and drawing one of them."""

from __future__ import annotations

import json
import random
from collections.abc import Iterator, Sequence
from pathlib import Path


def product_ids(metadata_root: Path, filename: str) -> Iterator[str]:
    """Yield the product id of every record the metadata holds.

    Args:
        metadata_root: Where the metadata stage writes what it fetched.
        filename: The metadata file each feature keeps its products in.

    Yields:
        The product id of each record, as the metadata spells it.
    """
    for source in metadata_root.rglob(filename):
        # Read the metadata file line by line, which is a JSON object per line.
        for line in source.read_text().splitlines():
            if line.strip():
                # The product id is in the `pdsid` field
                yield json.loads(line)["pdsid"]


def pick(pool: Sequence[str], seed: int, wanted: str) -> str:
    """Draw the one product a number picks out.

    Args:
        pool: The ids to draw from.
        seed: The number to draw with.
        wanted: What the pool holds, for the error when it holds nothing.

    Returns:
        The id drawn, which is the same one for the same number and pool.

    Raises:
        ValueError: When the pool holds nothing.
    """
    if not pool:
        raise ValueError(f"No {wanted} to draw from.")
    return random.Random(seed).choice(pool)

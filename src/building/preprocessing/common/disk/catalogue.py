"""Reading the observations the metadata stage wrote, and drawing one."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from utils.disk.files import read_jsonl


def product_ids(metadata_root: Path, filename: str) -> Iterator[str]:
    """Yield the product id of every record the metadata holds.

    Args:
        metadata_root: Where the metadata stage writes what it fetched.
        filename: The metadata file each feature keeps its products in.

    Yields:
        The product id of each record, as the metadata spells it.
    """
    for source in metadata_root.rglob(filename):
        for record in read_jsonl(source):
            # The product id is in the `pdsid` field
            yield record["pdsid"]


def observations(
    metadata_root: Path, filename: str, parse: Callable[[str], str | None]
) -> list[str]:
    """Read the ids of every observation the metadata names.

    Args:
        metadata_root: Where the metadata stage writes what it fetched.
        filename: The metadata file each feature keeps its products in.
        parse: What reads a product id as an observation id, or as None when
            the product is not one this instrument wants.

    Returns:
        The observation ids, sorted and without repeats.
    """
    found = {
        named
        for product_id in product_ids(metadata_root, filename)
        if (named := parse(product_id))
    }
    return sorted(found)


def sample(pool: Sequence[str], seed: int, wanted: str) -> str:
    """Draw the one observation a number picks out.

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

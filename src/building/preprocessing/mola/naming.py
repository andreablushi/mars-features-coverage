"""Naming the tiles PDS publishes the MOLA gridded record as."""

from __future__ import annotations

import re

# The two planes of one tile that are read, the height and how it was measured.
TOPOGRAPHY = "topography"
COUNTS = "counts"
KINDS = (TOPOGRAPHY, COUNTS)

# What each kind writes where the other writes the other.
_MARKERS = {TOPOGRAPHY: "t", COUNTS: "c"}

# How fine a grid each resolution letter stands for, in pixels per degree.
RESOLUTIONS = {"c": 4, "e": 16, "f": 32, "g": 64, "h": 128}

# A tile is named for the corner it starts at, how fine it is, and its width.
_ID = re.compile(r"^meg(?P<kind>[tc])(?P<tile>\d{2}[ns]\d{3}(?P<step>[cefgh])b)$")


def parse(product_id: str) -> str | None:
    """Read which tile a product id names.

    Args:
        product_id: The id to read, without its suffix, such as megt00n180hb.

    Returns:
        The tile id, or None when the id is not a topography or counts tile of
        the simple cylindrical grid.
    """
    match = _ID.match(product_id)
    return match["tile"] if match else None


def product(tile: str, kind: str = TOPOGRAPHY) -> str:
    """Return the id one plane of a tile is published under.

    Args:
        tile: The tile, such as 00n180hb.
        kind: Which plane, `TOPOGRAPHY` or `COUNTS`.

    Returns:
        The product id the archive knows that plane by, without its suffix.

    Raises:
        KeyError: When the kind is neither of the two.
    """
    return f"meg{_MARKERS[kind]}{tile}"


def resolution(tile: str) -> int:
    """Read how fine a grid one tile is written on.

    Args:
        tile: The tile, such as 00n180hb.

    Returns:
        The pixels per degree the tile holds.

    Raises:
        ValueError: When the tile is not one this can read.
    """
    match = _ID.match(product(tile))
    if not match:
        raise ValueError(f"{tile} is not a simple cylindrical MEGDR tile.")
    return RESOLUTIONS[match["step"]]

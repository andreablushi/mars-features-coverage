"""Naming the products ASU publishes one CTX scan as."""

from __future__ import annotations

import re

# The two products one scan is downloaded as, the pixels and what places them.
IMAGE = "image"
LABEL = "label"
KINDS = (IMAGE, LABEL)

# What each kind is suffixed with once it is on disk.
SUFFIXES = {IMAGE: ".tiff", LABEL: ".isis.hdr"}

# Which ASU directory each kind is kept in, and what it is called there.
DIRECTORIES = {IMAGE: "prj_full", LABEL: "stage"}
REMOTE_SUFFIXES = {IMAGE: ".tiff", LABEL: ".scyl.isis.hdr"}

# A scan is named for its mission phase, orbit, latitude and where it looked.
# Every phase is a letter and two digits, apart from orbit insertion.
_ID = re.compile(r"^(?:[a-z]\d{2}|moi)_\d{6}_\d{4}_[a-z]{2}_\d{2}[ns]\d{3}[we]$")

# The PDS volume a scan was archived on, which its download path runs through.
_VOLUME = re.compile(r"/(?P<volume>mrox_\d+)/")


def parse(product_id: str) -> str | None:
    """Read which scan a product id names.

    Args:
        product_id: The id to read, such as P01_001393_1655_XN_14S149W.

    Returns:
        The observation id as ASU spells it, or None when the id is not a CTX
        scan.
    """
    return product_id.upper() if _ID.match(product_id.lower()) else None


def volume(url: str) -> str:
    """Read which PDS volume a scan was archived on from where ODE offers it.

    Args:
        url: The download URL ODE gives the raw scan.

    Returns:
        The volume, such as mrox_0009.

    Raises:
        ValueError: When the URL runs through no volume this can read.
    """
    match = _VOLUME.search(url)
    if not match:
        raise ValueError(f"{url} names no CTX volume.")
    return match["volume"]


def remote(observation_id: str, volume_id: str, kind: str = IMAGE) -> str:
    """Return where ASU keeps one product of a scan.

    Args:
        observation_id: The observation, such as P01_001393_1655_XN_14S149W.
        volume_id: The PDS volume it was archived on.
        kind: Which product, `IMAGE` or `LABEL`.

    Returns:
        The path ASU serves that product from.

    Raises:
        KeyError: When the kind is neither of the two.
    """
    place, suffix = DIRECTORIES[kind], REMOTE_SUFFIXES[kind]
    return f"/mars/images/ctx/{volume_id}/{place}/{observation_id}{suffix}"

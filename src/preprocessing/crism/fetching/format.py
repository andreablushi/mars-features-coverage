"""Turning an observation id into the product ids and paths it stands for."""

from __future__ import annotations

import re
from pathlib import Path

from preprocessing.crism import configs

# The two detectors of one scan, infrared and visible.
DETECTORS = ("l", "s")

# The two halves of a product.
SUFFIXES = (".lbl", ".img")

# The subdirectory an observation keeps its geometry in, and that geometry's
# level, which has only ever been one.
GEOMETRY_DIR = "ddr"
GEOMETRY_LEVEL = "ddr1"

# Requiring `_if` and `_trr` is what rejects the radiance twins and the
# housekeeping tables the metadata lists beside them.
_ID = re.compile(
    r"^(?P<stem>\w+)_if(?P<code>\d+)(?P<detector>[ls]?)_(?P<level>trr\d+)$"
)


def parse(product_id: str) -> tuple[str, str] | None:
    """Read which observation and detector a product id names.

    Args:
        product_id: The id to read, such as msp000396ba_01_if214l_trr3.

    Returns:
        The observation id and the detector letter, or None when the id is not
        a multispectral survey I/F TRDR of one detector.
    """
    match = _ID.match(product_id)
    if not match or not match["detector"]:
        return None
    return f"{match['stem']}_if{match['code']}_{match['level']}", match["detector"]


def product(observation_id: str, detector: str, geometry: bool = False) -> str:
    """Return the id one detector of an observation is published under.

    Args:
        observation_id: The observation, such as msp000396ba_01_if214_trr3.
        detector: Which detector, `l` for infrared or `s` for visible.
        geometry: Whether to name the geometry rather than the observation.

    Returns:
        The product id ODE knows that detector by.

    Raises:
        ValueError: When the observation id is not one this can read.
    """
    match = _ID.match(observation_id)
    if not match:
        raise ValueError(f"{observation_id} is not a multispectral survey I/F TRDR.")
    kind, level = ("de", GEOMETRY_LEVEL) if geometry else ("if", match["level"])
    return f"{match['stem']}_{kind}{match['code']}{detector}_{level}"


def files(
    observation_id: str, detector: str, geometry: bool = False
) -> dict[str, Path]:
    """Return where each half of one detector's product belongs.

    Args:
        observation_id: The observation.
        detector: Which detector, `l` or `s`.
        geometry: Whether to place the geometry rather than the observation.

    Returns:
        The path for each suffix, keyed by suffix.
    """
    place = configs.CACHE_ROOT / observation_id
    stem = product(observation_id, detector, geometry)
    return {
        s: (place / GEOMETRY_DIR if geometry else place) / f"{stem}{s}"
        for s in SUFFIXES
    }


def labels(observation_id: str) -> dict[str, Path]:
    """Return where each detector's label belongs.

    Args:
        observation_id: The observation.

    Returns:
        The label path for each detector, keyed by detector.
    """
    return {detector: files(observation_id, detector)[".lbl"] for detector in DETECTORS}

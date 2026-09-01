"""Naming the products ODE publishes one CRISM observation as."""

from __future__ import annotations

import re
from pathlib import Path

# The two detectors of one scan, infrared and visible.
DETECTORS = ("l", "s")

# The two products one detector of a scan is published as.
OBSERVATION = "observation"
GEOMETRY = "geometry"
KINDS = (OBSERVATION, GEOMETRY)

# What each kind writes where the other writes the other.
_MARKERS = {OBSERVATION: "if", GEOMETRY: "de"}

# The level a geometry carries, which has only ever been one.
GEOMETRY_LEVEL = "ddr1"

# What a label calls the wavelength file it was calibrated against.
WAVELENGTH_KEY = "MRO:WAVELENGTH_FILE_NAME"

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


def product(observation_id: str, detector: str, kind: str = OBSERVATION) -> str:
    """Return the id one detector of an observation is published under.

    Args:
        observation_id: The observation, such as msp000396ba_01_if214_trr3.
        detector: Which detector, `l` for infrared or `s` for visible.
        kind: Which product, `OBSERVATION` or `GEOMETRY`.

    Returns:
        The product id ODE knows that detector by.

    Raises:
        ValueError: When the observation id is not one this can read.
        KeyError: When the kind is neither of the two.
    """
    match = _ID.match(observation_id)
    if not match:
        raise ValueError(f"{observation_id} is not a multispectral survey I/F TRDR.")
    marker = _MARKERS[kind]
    level = GEOMETRY_LEVEL if kind == GEOMETRY else match["level"]
    return f"{match['stem']}_{marker}{match['code']}{detector}_{level}"


def wavelength(label: dict[str, str]) -> str:
    """Read which wavelength file one label was calibrated against.

    Args:
        label: The parsed label of one detector's observation.

    Returns:
        The product id ODE knows that wavelength file by.

    Raises:
        KeyError: When the label names no wavelength file.
    """
    return Path(label[WAVELENGTH_KEY]).stem

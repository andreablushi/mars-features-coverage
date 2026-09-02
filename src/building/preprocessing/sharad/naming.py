"""Naming the products ODE publishes one SHARAD radargram as."""

from __future__ import annotations

import re

# The two products one track is published as.
OBSERVATION = "observation"
GEOMETRY = "geometry"
KINDS = (OBSERVATION, GEOMETRY)

# What each kind writes where the other writes the other.
_MARKERS = {OBSERVATION: "rgram", GEOMETRY: "geom"}

_ID = re.compile(r"^s_(?P<track>\d+)_(?P<kind>rgram|geom)$")


def parse(product_id: str) -> str | None:
    """Read which track a product id names.

    Args:
        product_id: The id to read, such as s_00577101_rgram.

    Returns:
        The observation id, or None when the id is not a radargram or the
        geometry beside one.
    """
    match = _ID.match(product_id)
    return f"s_{match['track']}" if match else None


def product(observation_id: str, kind: str = OBSERVATION) -> str:
    """Return the id one product of an observation is published under.

    Args:
        observation_id: The observation, such as s_00577101.
        kind: Which product, `OBSERVATION` or `GEOMETRY`.

    Returns:
        The product id ODE knows that product by.

    Raises:
        KeyError: When the kind is neither of the two.
    """
    return f"{observation_id}_{_MARKERS[kind]}"

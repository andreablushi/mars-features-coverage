"""The grid a simple cylindrical label lays a product out on."""

from __future__ import annotations

import numpy as np

Bounds = tuple[float, float, float, float]


def axes(
    lines: int, samples: int, north: float, west: float, step: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return the centre latitude of every line and longitude of every sample.

    A simple cylindrical grid is even in both directions, so the two axes are
    all that place it and a pixel sits where they cross.

    Args:
        lines: How many rows the product holds.
        samples: How many columns each row holds.
        north: The centre latitude of the first line, in degrees.
        west: The centre longitude of the first sample, in degrees.
        step: How many degrees one pixel spans.

    Returns:
        The latitude of every line, falling southward, and the longitude of
        every sample, rising eastward.
    """
    return north - np.arange(lines) * step, west + np.arange(samples) * step


def bounds(latitude: np.ndarray, longitude: np.ndarray, step: float) -> Bounds:
    """Return the edges the pixel centres of one grid reach out to.

    Args:
        latitude: The centre latitude of every line.
        longitude: The centre longitude of every sample.
        step: How many degrees one pixel spans.

    Returns:
        The southernmost, northernmost, westernmost and easternmost degree the
        grid covers, each half a pixel outside the outermost centres.
    """
    half = step / 2.0
    return (
        float(latitude.min()) - half,
        float(latitude.max()) + half,
        float(longitude.min()) - half,
        float(longitude.max()) + half,
    )


def check_bounds(reached: Bounds, claimed: Bounds, tolerance: float, what: str) -> None:
    """Refuse a grid that does not cover the corners its label claims.

    Args:
        reached: The edges the grid actually reaches.
        claimed: The edges the label says it covers.
        tolerance: How far apart the two may sit, in degrees.
        what: What is being placed, for the error when they sit further.

    Returns:
        None.

    Raises:
        ValueError: When the grid covers something other than its label says.
    """
    if not np.allclose(reached, claimed, atol=tolerance):
        raise ValueError(
            f"{what} reads over {reached}, where its label claims {claimed}."
        )

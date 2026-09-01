"""Placing one MOLA tile on the grid its label projects it onto."""

from __future__ import annotations

import numpy as np

# The only projection the gridded record is written in.
PROJECTION = "SIMPLE CYLINDRICAL"


def load(label: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    """Return the centre latitude of every line and longitude of every sample.

    Args:
        label: The parsed label of one plane.

    Returns:
        The latitude of every line and the longitude of every sample, both in
        degrees, so a pixel sits where the two cross.

    Raises:
        ValueError: When the label names a projection this cannot read.
    """
    if label["MAP_PROJECTION_TYPE"] != PROJECTION:
        raise ValueError(f"Cannot place a {label['MAP_PROJECTION_TYPE']} grid.")
    # How many degrees one pixel spans, the same in both directions.
    step = 1.0 / float(label["MAP_RESOLUTION"])
    # Where the projection puts its origin, counted in pixels from the corner.
    lines = np.arange(int(label["LINES"])) + 1.0
    samples = np.arange(int(label["LINE_SAMPLES"])) + 1.0
    # Latitude falls down the lines, and longitude rises across the samples.
    latitude = (
        float(label["CENTER_LATITUDE"])
        - (lines - float(label["LINE_PROJECTION_OFFSET"])) * step
    )
    longitude = (
        float(label["CENTER_LONGITUDE"])
        + (samples - float(label["SAMPLE_PROJECTION_OFFSET"])) * step
    )
    return latitude, longitude


def bounds(
    latitude: np.ndarray, longitude: np.ndarray, step: float
) -> tuple[float, float, float, float]:
    """Return the edges the pixel centres of one grid reach out to.

    Args:
        latitude: The centre latitude of every line.
        longitude: The centre longitude of every sample.
        step: How many degrees one pixel spans.

    Returns:
        The southernmost, northernmost, westernmost and easternmost degree the
        grid covers, each half a pixel outside the centres.
    """
    half = step / 2.0
    return (
        float(latitude.min()) - half,
        float(latitude.max()) + half,
        float(longitude.min()) - half,
        float(longitude.max()) + half,
    )

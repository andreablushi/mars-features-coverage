"""Placing one CTX scan on the grid its label projects it onto."""

from __future__ import annotations

import numpy as np

from preprocessing.common import grids

# The only projection ASU writes a CTX RDR in.
PROJECTION = "SimpleCylindrical"

# The only reading of latitude, longitude and their range this places.
CONVENTIONS = {
    "LatitudeType": "Planetocentric",
    "LongitudeDirection": "PositiveEast",
    "LongitudeDomain": "360",
}


def load(label: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    """Return the centre latitude of every line and longitude of every sample.

    Args:
        label: The parsed ISIS label of one scan.

    Returns:
        The latitude of every line and the longitude of every sample, both in
        degrees, so a pixel sits where the two cross.

    Raises:
        ValueError: When the label names a projection or a convention this
            cannot read.
    """
    if label["ProjectionName"] != PROJECTION:
        raise ValueError(f"Cannot place a {label['ProjectionName']} grid.")
    for key, wanted in CONVENTIONS.items():
        if label[key] != wanted:
            raise ValueError(f"Cannot place a grid whose {key} is {label[key]}.")
    # The corner the projection starts from, in metres east and north of it.
    radius = float(label["EquatorialRadius"])
    half = float(label["PixelResolution"]) / 2.0
    return grids.axes(
        int(label["Lines"]),
        int(label["Samples"]),
        np.degrees((float(label["UpperLeftCornerY"]) - half) / radius),
        float(label["CenterLongitude"])
        + np.degrees((float(label["UpperLeftCornerX"]) + half) / radius),
        pixel(label),
    )


def pixel(label: dict[str, str]) -> float:
    """Return how many degrees one pixel of a scan spans.

    Args:
        label: The parsed ISIS label of one scan.

    Returns:
        The width of a pixel in degrees, the same in both directions.
    """
    return float(
        np.degrees(float(label["PixelResolution"]) / float(label["EquatorialRadius"]))
    )

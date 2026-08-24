"""Spherical geometry on Mars: longitudes, projection, areas, and lengths."""

from __future__ import annotations

import math

import numpy as np

from analysis import configs

# A degree of longitude vanishes at a pole, so the correction is floored
MIN_COSINE = 0.05


def normalise_longitude(lon: np.ndarray | float) -> np.ndarray:
    """Wrap longitudes into the -180 to 180 degree range.

    Args:
        lon: One longitude in degrees, or an array of them.

    Returns:
        The wrapped longitudes as a float array.
    """
    return (np.asarray(lon, dtype=float) + 180.0) % 360.0 - 180.0


def longitude_stretch(lat: float) -> float:
    """Return how much a degree of longitude shrinks at one latitude.

    A degree of longitude covers cos(lat) of the ground a degree of latitude
    does, so a fixed ground distance needs that many more degrees of it. The
    cosine is floored, since near a pole the correction runs away.

    Args:
        lat: The latitude in degrees.

    Returns:
        The cosine of the latitude, never below MIN_COSINE.
    """
    return max(math.cos(math.radians(lat)), MIN_COSINE)


def longitude_span(west_lon: float, east_lon: float) -> float:
    """Return the eastward span in degrees from a west to an east longitude.

    Args:
        west_lon: The westernmost longitude in degrees.
        east_lon: The easternmost longitude in degrees.

    Returns:
        The eastward span in degrees, above zero and up to 360.
    """
    raw = east_lon - west_lon
    if raw >= 360.0 or raw == 0.0:
        return 360.0
    if raw > 0.0:
        return raw
    return raw % 360.0


def bbox_centre(
    min_lat: float, max_lat: float, west_lon: float, east_lon: float
) -> tuple[float, float]:
    """Return the centre of a feature bounding box.

    Args:
        min_lat: The southernmost latitude in degrees.
        max_lat: The northernmost latitude in degrees.
        west_lon: The westernmost longitude in degrees.
        east_lon: The easternmost longitude in degrees.

    Returns:
        The centre longitude in -180 to 180 degrees and the centre latitude.
    """
    centre_lon = west_lon + longitude_span(west_lon, east_lon) / 2.0
    return float(normalise_longitude(centre_lon)), (min_lat + max_lat) / 2.0


def _edge_samples(span_deg: float) -> int:
    """Return how many samples an edge needs to stay under the segment step.

    Args:
        span_deg: The angular length of the edge in degrees.

    Returns:
        The sample count, never fewer than two.
    """
    return max(2, math.ceil(abs(span_deg) / configs.MAX_SEGMENT_DEG) + 1)


def bbox_ring(
    min_lat: float, max_lat: float, west_lon: float, east_lon: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return a densified closed lon/lat ring tracing a bounding box.

    Args:
        min_lat: The southernmost latitude in degrees.
        max_lat: The northernmost latitude in degrees.
        west_lon: The westernmost longitude in degrees.
        east_lon: The easternmost longitude in degrees.

    Returns:
        The ring longitudes and latitudes, closed back onto the first point.
    """
    span = longitude_span(west_lon, east_lon)
    east = west_lon + span
    along = np.linspace(west_lon, east, _edge_samples(span))
    up = np.linspace(min_lat, max_lat, _edge_samples(max_lat - min_lat))
    lons = np.concatenate(
        [along, np.full(up.size, east), along[::-1], np.full(up.size, west_lon)]
    )
    lats = np.concatenate(
        [np.full(along.size, min_lat), up, np.full(along.size, max_lat), up[::-1]]
    )
    return lons, lats


def laea_forward(
    lon: np.ndarray | float,
    lat: np.ndarray | float,
    centre_lon: float,
    centre_lat: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Project lon/lat degrees into Lambert azimuthal equal-area metres.

    Args:
        lon: The longitudes in degrees.
        lat: The latitudes in degrees.
        centre_lon: The projection centre longitude in degrees.
        centre_lat: The projection centre latitude in degrees.

    Returns:
        The projected eastings and northings in metres.
    """
    delta = np.radians(np.asarray(lon, dtype=float) - centre_lon)
    phi = np.radians(np.asarray(lat, dtype=float))
    phi0 = math.radians(centre_lat)
    cos_c = math.sin(phi0) * np.sin(phi) + math.cos(phi0) * np.cos(phi) * np.cos(delta)
    scale = np.sqrt(2.0 / np.maximum(1.0 + cos_c, configs.LAEA_MIN_DENOMINATOR))
    x = configs.MARS_RADIUS_M * scale * np.cos(phi) * np.sin(delta)
    y = (
        configs.MARS_RADIUS_M
        * scale
        * (math.cos(phi0) * np.sin(phi) - math.sin(phi0) * np.cos(phi) * np.cos(delta))
    )
    return x, y


def haversine_length(lon: np.ndarray, lat: np.ndarray) -> float:
    """Return the great-circle length along a sequence of lon/lat points.

    Args:
        lon: The point longitudes in degrees.
        lat: The point latitudes in degrees.

    Returns:
        The summed length in metres, or 0.0 for fewer than two points.
    """
    if len(lon) < 2:
        return 0.0
    lam = np.radians(np.asarray(lon, dtype=float))
    phi = np.radians(np.asarray(lat, dtype=float))
    hav = (
        np.sin(np.diff(phi) / 2.0) ** 2
        + np.cos(phi[:-1]) * np.cos(phi[1:]) * np.sin(np.diff(lam) / 2.0) ** 2
    )
    steps = 2.0 * configs.MARS_RADIUS_M * np.arcsin(np.sqrt(np.clip(hav, 0.0, 1.0)))
    return float(steps.sum())


def laea_inverse(
    x: np.ndarray | float,
    y: np.ndarray | float,
    centre_lon: float,
    centre_lat: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Turn Lambert azimuthal equal-area metres back into lon/lat degrees.

    Args:
        x: The projected eastings in metres.
        y: The projected northings in metres.
        centre_lon: The projection centre longitude in degrees.
        centre_lat: The projection centre latitude in degrees.

    Returns:
        The longitudes and latitudes in degrees, the longitudes wrapped into
        the -180 to 180 range.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    phi0 = math.radians(centre_lat)
    rho = np.hypot(x, y)
    safe = np.where(rho == 0.0, 1.0, rho)
    c = 2.0 * np.arcsin(np.clip(rho / (2.0 * configs.MARS_RADIUS_M), -1.0, 1.0))
    sin_c, cos_c = np.sin(c), np.cos(c)
    lat = np.arcsin(
        np.clip(cos_c * math.sin(phi0) + y * sin_c * math.cos(phi0) / safe, -1.0, 1.0)
    )
    lon = np.radians(centre_lon) + np.arctan2(
        x * sin_c,
        safe * math.cos(phi0) * cos_c - y * math.sin(phi0) * sin_c,
    )
    return normalise_longitude(np.degrees(lon)), np.degrees(
        np.where(rho == 0.0, phi0, lat)
    )

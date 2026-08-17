"""Footprint geometry: parsing ODE WKT and cutting it down to a feature box."""

from __future__ import annotations

import math

import numpy as np
from shapely import box, get_parts, get_type_id, intersection, is_empty
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry

from analysis.utils import geodesy

_LINESTRING = 1
_POLYGON = 3
_FIRST_MULTIPART = 4


def flatten(geom: BaseGeometry) -> list[BaseGeometry]:
    """Expand a geometry into its non-empty single-part pieces.

    Args:
        geom: Any geometry, including nested collections.

    Returns:
        The flat list of single-part geometries.
    """
    if geom.is_empty:
        return []
    if isinstance(geom, BaseMultipartGeometry):
        return [piece for part in geom.geoms for piece in flatten(part)]
    return [geom]


def clip_boxes(
    min_lat: float,
    max_lat: float,
    west_lon: float,
    east_lon: float,
    *,
    margin_deg: float = 0.0,
) -> BaseGeometry:
    """Build the lon/lat region a footprint is cut against.

    Args:
        min_lat: The southernmost latitude in degrees.
        max_lat: The northernmost latitude in degrees.
        west_lon: The westernmost longitude in degrees.
        east_lon: The easternmost longitude in degrees.
        margin_deg: How far to widen the region, in degrees of latitude.

    Returns:
        The clipping region, as one rectangle or the union of two.
    """
    lat_limit = min(max(abs(min_lat), abs(max_lat)), 89.0)
    lon_margin = margin_deg / max(math.cos(math.radians(lat_limit)), 0.05)
    lat_lo = max(-90.0, min_lat - margin_deg)
    lat_hi = min(90.0, max_lat + margin_deg)
    span = geodesy.longitude_span(west_lon, east_lon) + 2.0 * lon_margin
    if span >= 360.0:
        return box(-180.0, lat_lo, 180.0, lat_hi)
    west = float(geodesy.normalise_longitude(west_lon - lon_margin))
    east = west + span
    if east <= 180.0:
        return box(west, lat_lo, east, lat_hi)
    return box(west, lat_lo, 180.0, lat_hi).union(
        box(-180.0, lat_lo, east - 360.0, lat_hi)
    )


def clipped_surface_parts(
    geoms: np.ndarray,
    tight_region: BaseGeometry,
    wide_region: BaseGeometry,
    widths_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Cut a whole set's footprints to a feature and say how wide to draw them.

    Args:
        geoms: The parsed footprint geometries in lon/lat degrees.
        tight_region: The feature box, used for footprints that have area.
        wide_region: The widened box, used for tracks that still need buffering.
        widths_m: The cross-track width to give each footprint's track.

    Returns:
        The clipped single-part shapes, the index of the footprint each came
        from, and the buffer radius in metres to draw it with.
    """
    parts, owners = _single_parts(geoms)
    kinds = get_type_id(parts)
    areal = np.zeros(len(geoms), dtype=bool)
    areal[owners[kinds == _POLYGON]] = True
    keep = np.where(areal[owners], kinds == _POLYGON, kinds == _LINESTRING)
    parts, owners = parts[keep], owners[keep]
    regions = np.asarray([wide_region, tight_region], dtype=object)
    clipped = intersection(parts, regions[areal[owners].astype(int)])
    alive = ~is_empty(clipped)
    owners = owners[alive]
    buffers = np.where(areal[owners], 0.0, np.asarray(widths_m)[owners] / 2.0)
    return clipped[alive], owners, buffers


def _single_parts(geoms: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Expand geometries into their non-empty single-part pieces.

    Args:
        geoms: The geometries to expand, including nested collections.

    Returns:
        The flat single-part geometries and the index of the input each came
        from.
    """
    parts = np.asarray(geoms, dtype=object)
    owners = np.arange(parts.size)
    while parts.size and (get_type_id(parts) >= _FIRST_MULTIPART).any():
        parts, index = get_parts(parts, return_index=True)
        owners = owners[index]
    alive = ~is_empty(parts) if parts.size else np.zeros(0, dtype=bool)
    return parts[alive], owners[alive]

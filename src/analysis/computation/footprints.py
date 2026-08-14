"""Footprint geometry: parsing ODE WKT and cutting it down to a feature box.

ODE publishes a footprint as an area, a line, or a collection mixing both. A
collection carrying any polygon is an imaging footprint whose stray line parts
are noise slivers, so the polygons win. A footprint made only of lines is a
sounder ground track, which becomes an area by being buffered to its swath.

Footprints are cut to the feature box in lon/lat before being projected, which
keeps a footprint far wider than its feature away from the antipode of the
projection centre where the projection is undefined.
"""

from __future__ import annotations

import math

from shapely import box, from_wkt
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry

from analysis.computation import geodesy


def parse(wkt: str) -> BaseGeometry:
    """Parse an ODE footprint into a geometry.

    Args:
        wkt: The well-known-text footprint, in -180 to 180 degree longitudes.

    Returns:
        The parsed geometry.
    """
    return from_wkt(wkt)


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

    A box spanning the antimeridian becomes two rectangles, because ODE splits
    its own footprints there and both sides must be kept. The margin widens the
    region so a track clipped now still covers the box edge once buffered.

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


def surface_shapes(
    geom: BaseGeometry,
    tight_region: BaseGeometry,
    wide_region: BaseGeometry,
    swath_width_m: float,
) -> tuple[list[BaseGeometry], float]:
    """Cut a footprint to a feature and say how wide to draw it.

    Args:
        geom: The parsed footprint geometry in lon/lat degrees.
        tight_region: The feature box, used for footprints that have area.
        wide_region: The widened box, used for tracks that still need buffering.
        swath_width_m: The cross-track width to give a sounder track.

    Returns:
        The clipped lon/lat shapes and the buffer radius in metres to draw
        them with, which is zero for footprints that already have area.
    """
    parts = flatten(geom)
    areas = [part for part in parts if part.geom_type == "Polygon"]
    if areas:
        return _clip(areas, tight_region), 0.0
    tracks = [part for part in parts if part.geom_type == "LineString"]
    return _clip(tracks, wide_region), swath_width_m / 2.0


def _clip(parts: list[BaseGeometry], region: BaseGeometry) -> list[BaseGeometry]:
    """Intersect every part with a region, dropping what falls outside.

    Args:
        parts: The single-part geometries to cut.
        region: The lon/lat region to cut them against.

    Returns:
        The non-empty intersections.
    """
    clipped = [part.intersection(region) for part in parts]
    return [part for part in clipped if not part.is_empty]

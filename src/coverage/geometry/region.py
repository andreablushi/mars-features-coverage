"""The feature a coverage measurement is made against, and the union over it."""

from __future__ import annotations

import numpy as np
from shapely import (
    Polygon,
    buffer,
    covers,
    intersection,
    is_valid,
    make_valid,
    prepare,
    segmentize,
    transform,
    union_all,
)
from shapely.geometry.base import BaseGeometry

from coverage import configs
from coverage.geometry import footprints
from coverage.utils import geodesy
from models.feature import Feature

_EMPTY = Polygon()


def _merge_owned_parts(
    parts: np.ndarray, owners: np.ndarray, shapes: np.ndarray
) -> None:
    """Put each footprint's parts back together as one shape.

    Args:
        parts: The projected single-part shapes.
        owners: The index of the footprint each part came from.
        shapes: The per-footprint results to fill in place.

    Returns:
        None.
    """
    order = np.argsort(owners, kind="stable")
    parts, owners = parts[order], owners[order]
    wanted = np.arange(shapes.size)
    starts = np.searchsorted(owners, wanted, side="left")
    ends = np.searchsorted(owners, wanted, side="right")
    counts = ends - starts
    shapes[counts == 1] = parts[starts[counts == 1]]
    for index in np.nonzero(counts > 1)[0]:
        shapes[index] = union_all(parts[starts[index] : ends[index]])


def _mend(geometry):
    """Rebuild a shape the projection left crossing itself.

    Args:
        geometry: One shape, or an array of them.

    Returns:
        The same shape or array, valid.
    """
    return make_valid(geometry, method="structure", keep_collapsed=False)


class FeatureRegion:
    """One feature's bounding box, projected into equal-area metres.

    Attributes:
        centre_lon: The projection centre longitude in degrees.
        centre_lat: The projection centre latitude in degrees.
        area_m2: The area of the bounding box in square metres.
    """

    def __init__(self, feature: Feature) -> None:
        """Project one feature's bounding box.

        Args:
            feature: The feature whose box the coverage is measured against.

        Returns:
            None.
        """
        min_lat, max_lat = feature.min_lat, feature.max_lat
        west_lon, east_lon = feature.west_lon, feature.east_lon
        self.centre_lon, self.centre_lat = geodesy.bbox_centre(
            min_lat, max_lat, west_lon, east_lon
        )
        lons, lats = geodesy.bbox_ring(min_lat, max_lat, west_lon, east_lon)
        x, y = geodesy.laea_forward(lons, lats, self.centre_lon, self.centre_lat)
        shape = Polygon(np.column_stack((x, y)))
        self._shape = shape if is_valid(shape) else _mend(shape)
        prepare(self._shape)
        self.area_m2 = self._shape.area
        self._tight = footprints.clip_boxes(min_lat, max_lat, west_lon, east_lon)
        self._wide = footprints.clip_boxes(
            min_lat,
            max_lat,
            west_lon,
            east_lon,
            margin_deg=configs.LINE_CLIP_MARGIN_DEG,
        )

    @property
    def shape(self) -> BaseGeometry:
        """Return the projected feature the footprints are cut to.

        Returns:
            The bounding box as a polygon in equal-area metres.
        """
        return self._shape

    def footprint_areas(
        self, geoms: np.ndarray, swath_widths_m: np.ndarray
    ) -> np.ndarray:
        """Return the ground a whole set of observations covers on the feature.

        Args:
            geoms: The parsed footprint geometries in lon/lat degrees.
            swath_widths_m: The cross-track width for each track, ignored for areas.

        Returns:
            One projected, clipped footprint per input, empty where it falls outside.
        """
        parts, owners, buffers = footprints.clipped_surface_parts(
            geoms, self._tight, self._wide, swath_widths_m
        )
        shapes = np.full(len(geoms), _EMPTY, dtype=object)
        if not parts.size:
            return shapes
        projected = transform(segmentize(parts, configs.MAX_SEGMENT_DEG), self._project)
        grown = buffers > 0.0
        if grown.any():
            projected[grown] = buffer(
                projected[grown],
                buffers[grown],
                quad_segs=configs.BUFFER_QUAD_SEGMENTS,
            )
        broken = ~is_valid(projected)
        if broken.any():
            projected[broken] = _mend(projected[broken])
        _merge_owned_parts(projected, owners, shapes)
        return self._clip_to_feature(shapes)

    def _clip_to_feature(self, shapes: np.ndarray) -> np.ndarray:
        """Cut projected footprints back to the feature they belong to.

        Args:
            shapes: The projected footprints.

        Returns:
            The footprints, each within the feature.
        """
        outside = ~covers(self._shape, shapes)
        if outside.any():
            shapes[outside] = intersection(shapes[outside], self._shape)
        return shapes

    def _project(self, coords: np.ndarray) -> np.ndarray:
        """Project an array of lon/lat pairs into the feature's projection.

        Args:
            coords: An array of lon/lat pairs in degrees.

        Returns:
            The matching array of projected eastings and northings in metres.
        """
        x, y = geodesy.laea_forward(
            coords[:, 0], coords[:, 1], self.centre_lon, self.centre_lat
        )
        return np.column_stack((x, y))

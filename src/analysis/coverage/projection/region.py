"""The feature a coverage measurement is made against, projected once."""

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

from analysis.coverage import configs
from analysis.coverage.projection.geometry import footprints, geodesy
from analysis.models.feature import Feature

_EMPTY = Polygon()


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
        shape: The bounding box as a polygon in equal-area metres.
        area_m2: The area of that box in square metres.
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
        box = Polygon(np.column_stack((x, y)))
        # A box wide enough to wrap the planet crosses itself once projected
        self.shape = box if is_valid(box) else _mend(box)
        prepare(self.shape)
        self.area_m2 = self.shape.area
        self._tight = footprints.clip_boxes(min_lat, max_lat, west_lon, east_lon)
        self._wide = footprints.clip_boxes(
            min_lat,
            max_lat,
            west_lon,
            east_lon,
            margin_deg=configs.LINE_CLIP_MARGIN_DEG,
        )

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
        # Each footprint's parts are put back together as the one shape they were
        order = np.argsort(owners, kind="stable")
        projected, owners = projected[order], owners[order]
        wanted = np.arange(shapes.size)
        starts = np.searchsorted(owners, wanted, side="left")
        ends = np.searchsorted(owners, wanted, side="right")
        counts = ends - starts
        shapes[counts == 1] = projected[starts[counts == 1]]
        for index in np.nonzero(counts > 1)[0]:
            shapes[index] = union_all(projected[starts[index] : ends[index]])
        # Whatever reached past the feature is cut back to it
        outside = ~covers(self.shape, shapes)
        if outside.any():
            shapes[outside] = intersection(shapes[outside], self.shape)
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

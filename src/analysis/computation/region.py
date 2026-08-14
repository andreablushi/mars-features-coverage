"""The feature a coverage measurement is made against, and the union over it.

Everything is measured in a Lambert azimuthal equal-area projection centred on
the feature, so a projected area is a true ground area and shapes near the
centre keep their form, which is what lets a buffered SHARAD track hold its
real width instead of being stretched by latitude.

Footprints are cut to the feature in lon/lat before being projected, which
keeps a footprint far wider than its feature away from the antipode of the
projection centre where the projection is undefined.
"""

from __future__ import annotations

import numpy as np
from shapely import Polygon, segmentize, transform, union_all
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.computation import footprints, geodesy

_EMPTY = Polygon()


class FeatureRegion:
    """One feature's bounding box, projected into equal-area metres.

    Attributes:
        centre_lon: The projection centre longitude in degrees.
        centre_lat: The projection centre latitude in degrees.
        area_m2: The area of the bounding box in square metres.
    """

    def __init__(
        self, min_lat: float, max_lat: float, west_lon: float, east_lon: float
    ) -> None:
        """Project one feature bounding box.

        Args:
            min_lat: The southernmost latitude in degrees.
            max_lat: The northernmost latitude in degrees.
            west_lon: The westernmost longitude in degrees.
            east_lon: The easternmost longitude in degrees.

        Returns:
            None.
        """
        self.centre_lon, self.centre_lat = geodesy.bbox_centre(
            min_lat, max_lat, west_lon, east_lon
        )
        lons, lats = geodesy.bbox_ring(min_lat, max_lat, west_lon, east_lon)
        x, y = geodesy.laea_forward(lons, lats, self.centre_lon, self.centre_lat)
        self._shape = Polygon(np.column_stack((x, y)))
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

    def footprint(self, geom: BaseGeometry, swath_width_m: float) -> BaseGeometry:
        """Return the ground one observation covers inside the feature.

        Args:
            geom: The parsed footprint geometry in lon/lat degrees.
            swath_width_m: The cross-track width to give a sounder track,
                ignored for footprints that already enclose area.

        Returns:
            The projected, clipped footprint, empty when it falls outside.
        """
        shapes, buffer_m = footprints.surface_shapes(
            geom, self._tight, self._wide, swath_width_m
        )
        if not shapes:
            return _EMPTY
        projected = [
            transform(segmentize(shape, configs.MAX_SEGMENT_DEG), self._project)
            for shape in shapes
        ]
        if buffer_m > 0.0:
            projected = [shape.buffer(buffer_m) for shape in projected]
        return union_all(projected).intersection(self._shape)

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

"""The feature a coverage measurement is made against, and the union over it.

Everything is measured in a Lambert azimuthal equal-area projection centred on
the feature, so a projected area is a true ground area and shapes near the
centre keep their form, which is what lets a buffered SHARAD track hold its
real width instead of being stretched by latitude.

Footprints are cut to the feature in lon/lat before being projected, which
keeps whole-planet basemaps away from the antipode of the projection centre
where the projection is undefined.
"""

from __future__ import annotations

import numpy as np
from shapely import Polygon, covers, prepare, segmentize, transform, union_all
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


class CoverageUnion:
    """A running union of the ground covered so far.

    What an observation adds is the growth of the union's area rather than a
    separate difference against it, so folding one in costs a single union.

    Most observations repeat ground their instrument has already seen, and a
    footprint the union already covers cannot change its area. Testing that
    first against a prepared index is far cheaper than the union it avoids,
    and it is exact: the skipped footprints contribute nothing by definition.

    Attributes:
        area_m2: The ground covered so far in square metres.
    """

    def __init__(self) -> None:
        """Start an empty union.

        Returns:
            None.
        """
        self._shape: BaseGeometry = _EMPTY
        self.area_m2 = 0.0

    @property
    def shape(self) -> BaseGeometry:
        """Return the union built so far.

        Returns:
            The accumulated geometry, empty until something is added.
        """
        return self._shape

    def add(self, shape: BaseGeometry) -> float:
        """Fold one footprint into the union.

        Args:
            shape: The projected footprint to add.

        Returns:
            The area in square metres the footprint covered that the union had
            not already reached.
        """
        if shape.is_empty or covers(self._shape, shape):
            return 0.0
        self._shape = union_all([self._shape, shape])
        prepare(self._shape)
        grown = self._shape.area
        fresh = max(grown - self.area_m2, 0.0)
        self.area_m2 = grown
        return fresh

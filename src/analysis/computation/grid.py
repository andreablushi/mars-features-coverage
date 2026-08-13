"""The equal-area raster a feature's coverage is measured on.

Coverage is counted in cells rather than by unioning polygons. Cells make the
cost linear in the number of observations instead of growing with the
complexity of an accumulated union, and they make rolling several instruments
up into one figure a bitwise or rather than a union redone from scratch.

The raster lives in a Lambert azimuthal equal-area projection centred on the
feature, so every cell covers the same true ground area and a cell count
converts straight into a fraction of the feature.

A footprint is returned as a patch covering only the cells it reaches rather
than as a full-size mask, because almost every footprint is small next to the
feature holding it and the accumulation would otherwise spend its time on
cells no observation ever touches.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
from shapely import segmentize, transform
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.computation import footprints, geodesy


@dataclass(frozen=True, slots=True)
class Patch:
    """The cells one footprint covers, positioned within a feature raster.

    Attributes:
        mask: The boolean window marking covered cells.
        row: The raster row the window starts at.
        column: The raster column the window starts at.
    """

    mask: np.ndarray
    row: int
    column: int

    @property
    def cells(self) -> int:
        """Count the cells the patch covers.

        Returns:
            The number of covered cells.
        """
        return int(np.count_nonzero(self.mask))

    def merge(self, target: np.ndarray) -> int:
        """Fold the patch into a running mask.

        Args:
            target: The full-size mask to fold into, modified in place.

        Returns:
            How many cells the patch covered that the mask had not.
        """
        if self.mask.size == 0:
            return 0
        rows, columns = self.mask.shape
        window = target[self.row : self.row + rows, self.column : self.column + columns]
        fresh = int(np.count_nonzero(self.mask & ~window))
        window |= self.mask
        return fresh


_EMPTY = Patch(np.zeros((0, 0), dtype=bool), 0, 0)


class FeatureGrid:
    """A raster covering one feature's bounding box.

    Attributes:
        centre_lon: The projection centre longitude in degrees.
        centre_lat: The projection centre latitude in degrees.
        area_m2: The exact area of the bounding box in square metres.
        cell_m: The side length of one cell in metres.
        mask: The boolean array marking cells inside the bounding box.
        total_cells: How many cells lie inside the bounding box.
    """

    def __init__(
        self, min_lat: float, max_lat: float, west_lon: float, east_lon: float
    ) -> None:
        """Build the raster for one feature bounding box.

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
        self.area_m2 = geodesy.ring_area(x, y)
        self._x_min, self._y_max = float(x.min()), float(y.max())
        width, height = float(x.max() - x.min()), float(y.max() - y.min())
        self.cell_m = max(width, height) / configs.GRID_MAX_DIM
        self._rows = max(1, math.ceil(height / self.cell_m))
        self._columns = max(1, math.ceil(width / self.cell_m))
        ring = self._to_pixels(np.column_stack((x, y)))
        self.mask = self._paint([ring], [], 0, 0, self._columns, self._rows)
        self.total_cells = int(self.mask.sum())
        self._tight = footprints.clip_boxes(min_lat, max_lat, west_lon, east_lon)
        self._wide = footprints.clip_boxes(
            min_lat,
            max_lat,
            west_lon,
            east_lon,
            margin_deg=configs.LINE_CLIP_MARGIN_DEG,
        )

    def empty_mask(self) -> np.ndarray:
        """Build a blank running mask sized for this raster.

        Returns:
            A false-filled boolean array matching the raster shape.
        """
        return np.zeros_like(self.mask)

    def rasterize(self, geom: BaseGeometry, swath_width_m: float) -> Patch:
        """Mark the cells a footprint covers inside the feature.

        Args:
            geom: The parsed footprint geometry in lon/lat degrees.
            swath_width_m: The cross-track width to give a sounder track,
                ignored for footprints that already enclose area.

        Returns:
            The patch of covered cells, already limited to the feature's own
            cells, or an empty patch when the footprint falls outside.
        """
        shapes, buffer_m = footprints.surface_shapes(
            geom, self._tight, self._wide, swath_width_m
        )
        rings: list[np.ndarray] = []
        holes: list[np.ndarray] = []
        for shape in shapes:
            projected = transform(
                segmentize(shape, configs.MAX_SEGMENT_DEG), self._project
            )
            if buffer_m > 0.0:
                projected = projected.buffer(buffer_m)
            for part in footprints.flatten(projected):
                if part.geom_type != "Polygon":
                    continue
                rings.append(self._to_pixels(np.asarray(part.exterior.coords)))
                holes.extend(
                    self._to_pixels(np.asarray(ring.coords)) for ring in part.interiors
                )
        return self._patch(rings, holes)

    def _patch(self, rings: list[np.ndarray], holes: list[np.ndarray]) -> Patch:
        """Draw pixel rings into the smallest window that holds them.

        Args:
            rings: The exterior rings in pixel coordinates.
            holes: The interior rings in pixel coordinates.

        Returns:
            The patch of covered cells, or an empty patch when the rings fall
            outside the raster entirely.
        """
        usable = [ring for ring in rings if len(ring) >= 3]
        if not usable:
            return _EMPTY
        stacked = np.concatenate(usable)
        left = max(0, math.floor(stacked[:, 0].min()))
        right = min(self._columns, math.ceil(stacked[:, 0].max()) + 1)
        top = max(0, math.floor(stacked[:, 1].min()))
        bottom = min(self._rows, math.ceil(stacked[:, 1].max()) + 1)
        if right <= left or bottom <= top:
            return _EMPTY
        drawn = self._paint(usable, holes, left, top, right - left, bottom - top)
        return Patch(drawn & self.mask[top:bottom, left:right], top, left)

    def _paint(
        self,
        rings: list[np.ndarray],
        holes: list[np.ndarray],
        left: int,
        top: int,
        columns: int,
        rows: int,
    ) -> np.ndarray:
        """Fill pixel rings onto a canvas of a given size and origin.

        Rings are drawn with their outline as well as their interior so a
        footprint narrower than one cell still registers rather than vanishing.

        Args:
            rings: The exterior rings in pixel coordinates.
            holes: The interior rings in pixel coordinates.
            left: The raster column the canvas starts at.
            top: The raster row the canvas starts at.
            columns: The canvas width in cells.
            rows: The canvas height in cells.

        Returns:
            A boolean array marking the filled cells.
        """
        canvas = Image.new("L", (columns, rows), 0)
        pen = ImageDraw.Draw(canvas)
        for ring in rings:
            _outline(pen, ring, left, top, 255)
        for ring in holes:
            _outline(pen, ring, left, top, 0)
        return np.asarray(canvas) > 0

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

    def _to_pixels(self, xy: np.ndarray) -> np.ndarray:
        """Convert projected metres into raster pixel coordinates.

        Args:
            xy: An array of projected easting and northing pairs in metres.

        Returns:
            The matching array of column and row pairs.
        """
        return np.column_stack(
            (
                (xy[:, 0] - self._x_min) / self.cell_m,
                (self._y_max - xy[:, 1]) / self.cell_m,
            )
        )


def _outline(
    pen: ImageDraw.ImageDraw, ring: np.ndarray, left: int, top: int, value: int
) -> None:
    """Draw one pixel ring onto a canvas offset to a window.

    Args:
        pen: The drawing context for the canvas.
        ring: The ring in raster pixel coordinates.
        left: The raster column the canvas starts at.
        top: The raster row the canvas starts at.
        value: The pixel value to paint the ring with.

    Returns:
        None.
    """
    if len(ring) < 3:
        return
    pen.polygon(
        [(float(c) - left, float(r) - top) for c, r in ring],
        fill=value,
        outline=value,
    )

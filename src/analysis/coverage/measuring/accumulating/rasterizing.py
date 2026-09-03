"""Every observation as cells of its feature, so any subset can be unioned later."""

from __future__ import annotations

import math

import numpy as np
from shapely import contains_xy, prepare
from shapely.geometry.base import BaseGeometry

from analysis.coverage import configs
from analysis.coverage.models.region import FeatureRegion
from analysis.utils.maths import mask as packing

_NONE = np.empty(0, dtype=np.int64)


class FeatureRaster:
    """One feature's grid, and which of its cells a footprint fills.

    Attributes:
        cells: How many of the grid's cells fall inside the feature.
        mask: Which of them those are, packed as one footprint's cells are.
        side: How many cells the grid holds along each axis.
        cell_km2: How much ground one cell covers.
    """

    def __init__(self, region: FeatureRegion, grid_cells: int) -> None:
        """Lay the grid over one projected feature.

        A feature is given a block of cells for every block of ground it spans,
        so a large feature is measured on a finer grid rather than a coarser one.

        Args:
            region: The feature the footprints were cut to.
            grid_cells: How many cells one block of the grid holds along each axis.

        Returns:
            None.
        """
        west, south, east, north = region.shape.bounds
        span_km = math.sqrt((east - west) * (north - south)) / 1000.0
        side = max(1, math.ceil(span_km / configs.GRID_KM)) * grid_cells
        self.side = side
        self._eastings = west + (np.arange(side) + 0.5) * (east - west) / side
        self._northings = south + (np.arange(side) + 0.5) * (north - south) / side
        self._cell_area = (east - west) * (north - south) / side**2
        self.cell_km2 = self._cell_area / 1e6
        inside = self._filled(region.shape)
        self.cells = int(inside.size)
        self.mask = packing.encode(inside, side**2)

    def burn(self, shape: BaseGeometry) -> bytes:
        """Record which of the feature's cells one footprint fills.

        Args:
            shape: The projected footprint, already cut to the feature.

        Returns:
            The cells it fills, packed as whichever form is smaller.
        """
        return packing.encode(self._filled(shape), self.side**2)

    def _filled(self, shape: BaseGeometry) -> np.ndarray:
        """Find the cells whose centre a shape covers.

        Args:
            shape: The projected shape to burn.

        Returns:
            The indices of the cells it fills, in ascending order.
        """
        if shape.is_empty:
            return _NONE
        west, south, east, north = shape.bounds
        columns = np.nonzero((self._eastings >= west) & (self._eastings <= east))[0]
        rows = np.nonzero((self._northings >= south) & (self._northings <= north))[0]
        if columns.size and rows.size:
            eastings, northings = np.meshgrid(
                self._eastings[columns], self._northings[rows]
            )
            prepare(shape)
            inside = contains_xy(shape, eastings, northings)
            if inside.any():
                down, crosswise = np.nonzero(inside)
                return rows[down] * self.side + columns[crosswise]
        # A footprint holding no cell centre is given the one cell it sits in
        if shape.area >= self._cell_area * configs.MIN_CELL_SHARE:
            point = shape.representative_point()
            row = int(np.abs(self._northings - point.y).argmin())
            column = int(np.abs(self._eastings - point.x).argmin())
            return np.array([row * self.side + column])
        return _NONE

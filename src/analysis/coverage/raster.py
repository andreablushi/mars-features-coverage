"""Every observation as cells of its feature, so any subset can be unioned later."""

from __future__ import annotations

import math

import numpy as np
from shapely import contains_xy, prepare
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.geometry.region import FeatureRegion
from utils.maths import mask as packing


def side_for(area_m2: float) -> int:
    """Choose how many cells a feature's grid gets along each axis.

    The count follows the cube root of the feature's width, which is the
    compromise between a fixed cell count, that leaves a continent's cells
    hundreds of kilometres across, and a fixed cell size, that would ask a
    continent for millions of them.

    Args:
        area_m2: The feature's area in square metres.

    Returns:
        The number of cells along each axis, never fewer than two.
    """
    width_km = math.sqrt(max(area_m2, 0.0)) / 1000.0
    if width_km <= 0.0:
        return 2
    side = configs.RASTER_CELL_FACTOR * width_km**configs.RASTER_CELL_EXPONENT
    return max(2, round(side))


class FeatureRaster:
    """One feature's grid, and which of its cells a footprint fills.

    Attributes:
        cells: How many of the grid's cells fall inside the feature, which is
            what a covered count is a share of.
    """

    def __init__(self, region: FeatureRegion) -> None:
        """Lay the grid over one projected feature.

        Args:
            region: The feature the footprints were cut to.

        Returns:
            None.
        """
        side = side_for(region.area_m2)
        west, south, east, north = region.shape.bounds
        self._side = side
        self._eastings = west + (np.arange(side) + 0.5) * (east - west) / side
        self._northings = south + (np.arange(side) + 0.5) * (north - south) / side
        self._cell_area = (east - west) * (north - south) / side**2
        self.cells = int(self._filled(region.shape).sum())

    def burn(self, shape: BaseGeometry) -> bytes:
        """Record which of the feature's cells one footprint fills.

        Args:
            shape: The projected footprint, already cut to the feature.

        Returns:
            The cells it fills, packed as whichever form is smaller.
        """
        return packing.encode(self._filled(shape))

    def _filled(self, shape: BaseGeometry) -> np.ndarray:
        """Find the cells whose centre a shape covers.

        Args:
            shape: The projected shape to burn.

        Returns:
            One flag per cell, row by row, flattened.
        """
        grid = np.zeros((self._side, self._side), dtype=bool)
        if shape.is_empty:
            return grid.ravel()
        west, south, east, north = shape.bounds
        columns = _between(self._eastings, west, east)
        rows = _between(self._northings, south, north)
        if columns.size and rows.size:
            eastings, northings = np.meshgrid(
                self._eastings[columns], self._northings[rows]
            )
            prepare(shape)
            grid[np.ix_(rows, columns)] = contains_xy(shape, eastings, northings)
        if not grid.any() and shape.area >= self._cell_area * configs.MIN_CELL_SHARE:
            self._nearest(grid, shape)
        return grid.ravel()

    def _nearest(self, grid: np.ndarray, shape: BaseGeometry) -> None:
        """Give a footprint holding no cell centre the one cell it sits in.

        Only a footprint worth about a cell is given one. On a feature whose
        cells still dwarf it, crediting it with a whole cell would claim far
        more ground than it reached, so it is left holding none.

        Args:
            grid: The cells found so far, written in place.
            shape: The projected shape being burned.

        Returns:
            None.
        """
        point = shape.representative_point()
        row = int(np.abs(self._northings - point.y).argmin())
        column = int(np.abs(self._eastings - point.x).argmin())
        grid[row, column] = True


def _between(values: np.ndarray, low: float, high: float) -> np.ndarray:
    """Return the indices of the cell centres falling inside one span.

    Args:
        values: The cell centres along one axis, in order.
        low: The near edge of the span.
        high: The far edge of the span.

    Returns:
        The indices of the centres between the two, in order.
    """
    return np.nonzero((values >= low) & (values <= high))[0]

"""Every observation as cells of its feature, so any subset can be unioned later."""

from __future__ import annotations

import numpy as np
from shapely import contains_xy, prepare
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.geometry.region import FeatureRegion


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
        side = configs.RASTER_SIDE
        west, south, east, north = region.shape.bounds
        self._side = side
        self._eastings = west + (np.arange(side) + 0.5) * (east - west) / side
        self._northings = south + (np.arange(side) + 0.5) * (north - south) / side
        self.cells = int(self._filled(region.shape).sum())

    def burn(self, shape: BaseGeometry) -> bytes:
        """Record which of the feature's cells one footprint fills.

        Args:
            shape: The projected footprint, already cut to the feature.

        Returns:
            The cells it fills, one bit each, packed row by row.
        """
        return np.packbits(self._filled(shape)).tobytes()

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
        if not grid.any():
            self._nearest(grid, shape)
        return grid.ravel()

    def _nearest(self, grid: np.ndarray, shape: BaseGeometry) -> None:
        """Give a footprint holding no cell centre the cell it sits in.

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

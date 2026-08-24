"""Every observation as cells of its feature, so any subset can be unioned later."""

from __future__ import annotations

import math

import numpy as np
from shapely import contains_xy, prepare
from shapely.geometry.base import BaseGeometry

import utils.disk.settings as settings
from analysis import configs
from analysis.geometry.region import FeatureRegion
from utils.maths import mask as packing

_NONE = np.empty(0, dtype=np.int64)


def grid_for(span_m: float, tile_km: int, tile_cells: int) -> tuple[int, int]:
    """Cut a feature into tiles, and give every tile the same grid.

    The tiles come first and the cells follow them, so a cell is the same
    share of a tile whatever the feature was cut from, and one measurement of
    a tile means what it means anywhere else. A feature narrower than a tile
    is one tile, and keeps a whole tile's worth of cells.

    Args:
        span_m: How wide the feature's box is, as the geometric mean of its
            two axes in metres.
        tile_km: How wide one tile is, in kilometres.
        tile_cells: How many cells one tile holds along each axis.

    Returns:
        How many tiles the feature is cut into along each axis, and how many
        cells that gives the grid along each axis.
    """
    span_km = max(span_m, 0.0) / 1000.0
    across = max(1, math.ceil(span_km / tile_km))
    return across, across * tile_cells


class FeatureRaster:
    """One feature's grid, and which of its cells a footprint fills.

    Attributes:
        cells: How many of the grid's cells fall inside the feature, which is
            what a covered count is a share of.
        mask: Which of them those are, packed as one footprint's cells are, so
            a tile can be credited with the ground the feature really has in
            it rather than with its whole block of the grid.
        side: How many cells the grid holds along each axis.
        across: How many tiles the feature is cut into along each axis.
        cell_km2: How much ground one cell covers.
    """

    def __init__(self, region: FeatureRegion) -> None:
        """Lay the grid over one projected feature.

        Args:
            region: The feature the footprints were cut to.

        Returns:
            None.
        """
        west, south, east, north = region.shape.bounds
        config = settings.load()
        self.across, side = grid_for(
            math.sqrt((east - west) * (north - south)),
            config.tile_km,
            config.tile_cells,
        )
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
        columns = _between(self._eastings, west, east)
        rows = _between(self._northings, south, north)
        if columns.size and rows.size:
            eastings, northings = np.meshgrid(
                self._eastings[columns], self._northings[rows]
            )
            prepare(shape)
            inside = contains_xy(shape, eastings, northings)
            if inside.any():
                down, crosswise = np.nonzero(inside)
                return rows[down] * self.side + columns[crosswise]
        if shape.area >= self._cell_area * configs.MIN_CELL_SHARE:
            return self._nearest(shape)
        return _NONE

    def _nearest(self, shape: BaseGeometry) -> np.ndarray:
        """Give a footprint holding no cell centre the one cell it sits in.

        Only a footprint worth about a cell is given one. On a feature whose
        cells still dwarf it, crediting it with a whole cell would claim far
        more ground than it reached, so it is left holding none.

        Args:
            shape: The projected shape being burned.

        Returns:
            The one cell it sits in.
        """
        point = shape.representative_point()
        row = int(np.abs(self._northings - point.y).argmin())
        column = int(np.abs(self._eastings - point.x).argmin())
        return np.array([row * self.side + column])


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

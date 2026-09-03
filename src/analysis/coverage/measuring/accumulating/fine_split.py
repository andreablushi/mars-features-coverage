"""Every observation as cells of its feature, so any subset can be unioned later."""

from __future__ import annotations

import math

import numpy as np
from shapely import contains_xy, prepare
from shapely.geometry.base import BaseGeometry

from analysis.coverage import configs
from analysis.coverage.models.grid import Grid
from analysis.coverage.models.region import FeatureRegion
from analysis.utils.maths import mask as packing

_NONE = np.empty(0, dtype=np.int64)


def grid_over(region: FeatureRegion, grid_cells: int) -> Grid:
    """Give one feature a grid fine enough for the ground it covers.

    A feature is given a block of cells for every block of ground it spans, so a
    large feature is measured on a finer grid rather than a coarser one.

    Args:
        region: The feature the footprints were cut to.
        grid_cells: How many cells one block of the grid holds along each axis.

    Returns:
        The grid the feature is measured on.
    """
    west, south, east, north = region.shape.bounds
    span_km = math.sqrt((east - west) * (north - south)) / 1000.0
    return Grid(
        west=west,
        south=south,
        east=east,
        north=north,
        side=max(1, math.ceil(span_km / configs.GRID_KM)) * grid_cells,
    )


def filled(grid: Grid, shape: BaseGeometry) -> np.ndarray:
    """Find the cells of the grid whose centre a shape covers.

    Args:
        grid: The grid the feature is measured on.
        shape: The projected shape to burn, already cut to the feature.

    Returns:
        The indices of the cells it fills, in ascending order.
    """
    if shape.is_empty:
        return _NONE
    eastings, northings = grid.centres
    west, south, east, north = shape.bounds
    columns = np.nonzero((eastings >= west) & (eastings <= east))[0]
    rows = np.nonzero((northings >= south) & (northings <= north))[0]
    if columns.size and rows.size:
        across, down = np.meshgrid(eastings[columns], northings[rows])
        prepare(shape)
        inside = contains_xy(shape, across, down)
        if inside.any():
            line, crosswise = np.nonzero(inside)
            return rows[line] * grid.side + columns[crosswise]
    # A footprint holding no cell centre is given the one cell it sits in
    if shape.area >= grid.cell_area_m2 * configs.MIN_CELL_SHARE:
        point = shape.representative_point()
        row = int(np.abs(northings - point.y).argmin())
        column = int(np.abs(eastings - point.x).argmin())
        return np.array([row * grid.side + column])
    return _NONE


def pack(grid: Grid, cells: np.ndarray) -> bytes:
    """Pack the cells a shape fills into whichever form is smaller.

    Args:
        grid: The grid those cells belong to.
        cells: The indices of the cells filled, in ascending order.

    Returns:
        The cells packed as a bitmap or as a list, whichever is shorter.
    """
    return packing.encode(cells, grid.side**2)

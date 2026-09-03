"""The grids a coverage measurement counts cells on: one feature's, and Mars'."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property

import numpy as np
from shapely import box


@dataclass(frozen=True)
class Grid:
    """A regular grid of cells covering one feature's projected bounding box.

    Attributes:
        west: The westernmost easting the grid spans, in metres.
        south: The southernmost northing it spans, in metres.
        east: The easternmost easting it spans, in metres.
        north: The northernmost northing it spans, in metres.
        side: How many cells it holds along each axis.
    """

    west: float
    south: float
    east: float
    north: float
    side: int

    @cached_property
    def cell_area_m2(self) -> float:
        """Return how much ground one cell of the grid covers.

        Returns:
            The area of one cell in square metres.
        """
        return (self.east - self.west) * (self.north - self.south) / self.side**2

    @cached_property
    def centres(self) -> tuple[np.ndarray, np.ndarray]:
        """Return where the centre of every cell falls, along each axis.

        Returns:
            The cell centre eastings, then the cell centre northings, in metres.
        """
        steps = np.arange(self.side) + 0.5
        return (
            self.west + steps * (self.east - self.west) / self.side,
            self.south + steps * (self.north - self.south) / self.side,
        )

    @cached_property
    def rectangles(self) -> np.ndarray:
        """Return every cell of the grid as a rectangle.

        Returns:
            One box per cell, walked row by row from the south west corner.
        """
        step_x = (self.east - self.west) / self.side
        step_y = (self.north - self.south) / self.side
        return np.asarray(
            [
                box(
                    self.west + column * step_x,
                    self.south + row * step_y,
                    self.west + (column + 1) * step_x,
                    self.south + (row + 1) * step_y,
                )
                for row in range(self.side)
                for column in range(self.side)
            ],
            dtype=object,
        )


@dataclass(frozen=True)
class PlanetGrid:
    """A cylindrical equal-area grid of the whole of a planet.

    The grid is equal area, so a cell covers the same ground wherever it falls,
    which is what lets the cells of overlapping features simply be counted.

    Attributes:
        radius_km: The planet's radius in kilometres.
        across: How many cells the grid holds around the equator.
        down: How many it holds from pole to pole.
    """

    radius_km: float
    across: int
    down: int

    @cached_property
    def cells(self) -> int:
        """Return how many cells the grid holds in all.

        Returns:
            The number of cells over the whole planet.
        """
        return self.across * self.down

    @cached_property
    def cell_km2(self) -> float:
        """Return how much ground one cell of the grid covers.

        Returns:
            The area of one cell in square kilometres.
        """
        return 4.0 * math.pi * self.radius_km**2 / self.cells

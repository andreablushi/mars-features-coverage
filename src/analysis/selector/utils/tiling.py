"""Cutting a feature into patches one window can still say something about."""

from __future__ import annotations

import math

import numpy as np

from analysis.selector.models.tiles import Grid, Tile
from analysis.utils.maths import mask as packing


def split(side: int, tile_km: float, cell_km2: float, grid_mask: bytes) -> Grid:
    """Cut a feature's grid into tiles no wider than the strategy asks.

    The grid is cut into the fewest tiles per axis that divide it evenly and still
    stay inside the width the strategy allows.

    Args:
        side: How many cells the feature's grid holds along each axis.
        tile_km: The widest a tile may be, in kilometres.
        cell_km2: How much ground one cell of the grid covers.
        grid_mask: Which cells of the grid fall inside the feature.

    Returns:
        The grid, holding a tile per patch and the tile every cell fell in.
    """
    wanted = side * math.sqrt(cell_km2) / tile_km
    evenly = [count for count in range(1, side + 1) if side % count == 0]
    across = min((count for count in evenly if count >= wanted), default=side)
    filled = packing.cells_of(grid_mask)
    # Say which tile every row and column of cells falls in, and where in it
    wide = side // across
    blocks = [index // wide for index in range(side)]
    spots = [index % wide for index in range(side)]
    owners = [
        blocks[row] * across + blocks[column]
        for row in range(side)
        for column in range(side)
    ]
    # Measure every patch on the ground the feature really has inside it
    held = np.bincount(np.asarray(owners)[filled], minlength=across * across)
    return Grid(
        tiles=[
            Tile(cells=wide * wide, area_km2=int(inside) * cell_km2) for inside in held
        ],
        across=across,
        owners=owners,
        places=[
            spots[row] * wide + spots[column]
            for row in range(side)
            for column in range(side)
        ],
        cell_km2=cell_km2,
        inside=frozenset(filled.tolist()),
    )

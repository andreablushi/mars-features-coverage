"""Cutting a feature into patches one window can still say something about."""

from __future__ import annotations

import math

from survey.models.tiles import Patchwork, Tile


def split(side: int, across: int, cell_km2: float) -> Patchwork:
    """Cut a feature's grid into the tiles the grid was sized for.

    The grid is burned for the tiling rather than for the feature, so every
    tile holds the same square of cells and nothing is left over.

    Args:
        side: How many cells the feature's grid holds along each axis.
        across: How many tiles it is cut into along each axis.
        cell_km2: How much ground one cell of the grid covers.

    Returns:
        The patchwork, holding a tile per patch and the tile every cell fell
        in.
    """
    # Measure one patch of the grid, which is every patch of it
    wide = side // across
    area_km2 = wide * wide * cell_km2
    tile = Tile(cells=wide * wide, area_km2=area_km2, width_km=math.sqrt(area_km2))
    # Say which tile every row and column of cells falls in, and where in it
    blocks = [index // wide for index in range(side)]
    spots = [index % wide for index in range(side)]
    return Patchwork(
        tiles=[tile] * (across * across),
        across=across,
        owners=[
            blocks[row] * across + blocks[column]
            for row in range(side)
            for column in range(side)
        ],
        places=[
            spots[row] * wide + spots[column]
            for row in range(side)
            for column in range(side)
        ],
        cell_km2=cell_km2,
    )

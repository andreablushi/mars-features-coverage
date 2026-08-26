"""Cutting a feature into patches one window can still say something about."""

from __future__ import annotations

import math

import numpy as np

from survey.models.tiles import Patchwork, Tile
from utils.maths import mask as packing


def split(side: int, tile_km: float, cell_km2: float, grid_mask: bytes) -> Patchwork:
    """Cut a feature's grid into tiles no wider than the strategy asks.

    Args:
        side: How many cells the feature's grid holds along each axis.
        tile_km: The widest a tile may be, in kilometres.
        cell_km2: How much ground one cell of the grid covers.
        grid_mask: Which cells of the grid fall inside the feature.

    Returns:
        The patchwork, holding a tile per patch and the tile every cell fell in.
    """
    across = _across(side, tile_km, cell_km2)
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
    return Patchwork(
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


def _across(side: int, tile_km: float, cell_km2: float) -> int:
    """Choose how many tiles a feature is cut into along each axis.

    Args:
        side: How many cells the feature's grid holds along each axis.
        tile_km: The widest a tile may be, in kilometres.
        cell_km2: How much ground one cell of the grid covers.

    Returns:
        The fewest tiles per axis that divide the grid evenly and stay inside the width.
    """
    wanted = side * math.sqrt(cell_km2) / tile_km
    evenly = [count for count in range(1, side + 1) if side % count == 0]
    return min((count for count in evenly if count >= wanted), default=side)

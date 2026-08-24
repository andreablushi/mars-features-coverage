"""Cutting a feature into patches one window can still say something about."""

from __future__ import annotations

import math

from analysis.coverage import raster
from survey import configs
from survey.models.tiles import Patchwork, Tile


def split(area_km2: float, mask_cells: int) -> Patchwork:
    """Cut a feature's grid into tiles of about the width the config asks for.

    Args:
        area_km2: How much ground the feature covers.
        mask_cells: How many cells of its grid fall inside it, which is what
            the ground is spread over.

    Returns:
        The patchwork, holding a tile per patch and the tile every cell fell
        in.
    """
    side = raster.side_for(area_km2 * 1e6)
    cell_km2 = area_km2 / mask_cells
    # Work out how many tiles a feature is cut into along each axis
    across = max(1, round(side * math.sqrt(cell_km2) / configs.TILE_KM))
    # Cut a row of cells into that many blocks, leaving no cell over
    edges = [round(step * side / across) for step in range(across + 1)]
    # Measure every patch of the grid, row by row, south first
    tiles: list[Tile] = []
    for row in range(across):
        for column in range(across):
            cells = (edges[column + 1] - edges[column]) * (edges[row + 1] - edges[row])
            area = cells * cell_km2
            tiles.append(Tile(cells=cells, area_km2=area, width_km=math.sqrt(area)))
    # Say which tile every cell of the grid falls in, and where in it
    blocks = [
        max(block for block in range(across) if edges[block] <= step)
        for step in range(side)
    ]
    owners, places = [0] * (side * side), [0] * (side * side)
    for row in range(side):
        down = blocks[row]
        for column in range(side):
            crosswise = blocks[column]
            wide = edges[crosswise + 1] - edges[crosswise]
            owners[row * side + column] = down * across + crosswise
            places[row * side + column] = (row - edges[down]) * wide + (
                column - edges[crosswise]
            )
    return Patchwork(
        tiles=tiles,
        across=across,
        owners=owners,
        places=places,
        cell_km2=cell_km2,
    )

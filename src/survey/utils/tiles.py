"""Cutting a feature into patches one window can still say something about."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from analysis.coverage import raster
from survey import configs


@dataclass(frozen=True, slots=True)
class Tile:
    """One patch of a feature, and what a window over it is measured against.

    Attributes:
        cells: How many cells of the feature's grid it holds.
        area_km2: How much ground it covers.
        width_km: How wide it is, which a sounder track has to cross enough of.
    """

    cells: int
    area_km2: float
    width_km: float


@dataclass(frozen=True, slots=True)
class Tiling:
    """A feature's grid cut into tiles, and where every cell of it landed.

    Attributes:
        tiles: The patches the feature was cut into, row by row, south first.
        across: How many of them there are along each axis.
        owners: The tile each cell of the feature's grid falls in, by cell.
        places: Where each cell sits in its own tile's grid, by cell.
        cell_km2: How much ground one cell of the feature's grid covers.
    """

    tiles: list[Tile]
    across: int
    owners: list[int]
    places: list[int]
    cell_km2: float

    def sort(self, cells: Sequence[int]) -> dict[int, list[int]]:
        """Split the cells one footprint fills between the tiles they fall in.

        Args:
            cells: The cells of the feature's grid the footprint fills.

        Returns:
            The cells it fills in each tile it reaches, in that tile's own
            numbering, by tile.
        """
        found: dict[int, list[int]] = {}
        for cell in cells:
            found.setdefault(self.owners[cell], []).append(self.places[cell])
        return found


def split(area_km2: float, mask_cells: int) -> Tiling:
    """Cut a feature's grid into tiles of about the width the config asks for.

    Above a few tens of kilometres one window per feature says nothing: the
    far side was observed years from the near side, so a single window either
    leaves most of the feature out or stretches over ground nothing looked at
    together. The feature is therefore cut up first and searched a tile at a
    time.

    Every cell falls in exactly one tile and every tile is a whole number of
    cells wide, so the tiles leave no ground over between them and a feature
    narrower than one tile is cut into exactly one.

    Args:
        area_km2: How much ground the feature covers.
        mask_cells: How many cells of its grid fall inside it, which is what
            the ground is spread over.

    Returns:
        The tiling, holding a tile per patch and the tile every cell fell in.
    """
    side = raster.side_for(area_km2 * 1e6)
    cell_km2 = area_km2 / mask_cells
    across = _across(side * math.sqrt(cell_km2))
    edges = _edges(side, across)
    tiles = [
        _tile(edges[column + 1] - edges[column], edges[row + 1] - edges[row], cell_km2)
        for row in range(across)
        for column in range(across)
    ]
    owners, places = _placed(side, across, edges)
    return Tiling(
        tiles=tiles,
        across=across,
        owners=owners,
        places=places,
        cell_km2=cell_km2,
    )


def _tile(columns: int, rows: int, cell_km2: float) -> Tile:
    """Measure one patch of the grid.

    Args:
        columns: How many cells wide it is.
        rows: How many cells tall it is.
        cell_km2: How much ground one cell covers.

    Returns:
        The tile.
    """
    area_km2 = columns * rows * cell_km2
    return Tile(cells=columns * rows, area_km2=area_km2, width_km=math.sqrt(area_km2))


def _across(width_km: float) -> int:
    """Work out how many tiles a feature is cut into along each axis.

    Args:
        width_km: How wide the feature is.

    Returns:
        The count, never fewer than one, so a feature smaller than a tile is
        searched whole.
    """
    return max(1, round(width_km / configs.TILE_KM))


def _edges(side: int, across: int) -> list[int]:
    """Cut a row of cells into that many blocks, leaving no cell over.

    Args:
        side: How many cells the grid holds along one axis.
        across: How many blocks to cut them into.

    Returns:
        Where every block starts and where the last one ends, so that the
        blocks differ by at most one cell and cover the row between them.
    """
    return [round(step * side / across) for step in range(across + 1)]


def _placed(
    side: int, across: int, edges: Sequence[int]
) -> tuple[list[int], list[int]]:
    """Say which tile every cell of the grid falls in, and where in it.

    Args:
        side: How many cells the grid holds along one axis.
        across: How many tiles the grid is cut into along one axis.
        edges: Where every block of cells starts and where the last one ends.

    Returns:
        The tile each cell falls in and where it sits in that tile's own grid,
        both by cell.
    """
    blocks = [
        max(block for block in range(across) if edges[block] <= step)
        for step in range(side)
    ]
    owners, places = [0] * (side * side), [0] * (side * side)
    for row in range(side):
        down = blocks[row]
        for column in range(side):
            crosswise = blocks[column]
            tile = down * across + crosswise
            wide = edges[crosswise + 1] - edges[crosswise]
            owners[row * side + column] = tile
            places[row * side + column] = (row - edges[down]) * wide + (
                column - edges[crosswise]
            )
    return owners, places

"""The patches a feature is searched in, and where every cell of it landed."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tile:
    """One patch of a feature, and what a window over it is measured against.

    Attributes:
        cells: How many cells of the feature's grid its block holds.
        area_km2: How much ground the feature really has inside it.
    """

    cells: int
    area_km2: float


@dataclass(frozen=True, slots=True)
class Grid:
    """A feature's grid cut into tiles, and where every cell of it landed.

    Attributes:
        tiles: The patches the feature was cut into, row by row, south first.
        across: How many of them there are along each axis.
        owners: The tile each cell of the feature's grid falls in, by cell.
        places: Where each cell sits in its own tile's grid, by cell.
        cell_km2: How much ground one cell of the feature's grid covers.
        inside: Which cells of that grid the feature really covers.
    """

    tiles: list[Tile]
    across: int
    owners: list[int]
    places: list[int]
    cell_km2: float
    inside: frozenset[int]

    def scatter_cells(self, cells: Sequence[int]) -> dict[int, list[int]]:
        """Split the cells one footprint fills between the tiles they fall in.

        Args:
            cells: The cells of the feature's grid the footprint fills.

        Returns:
            The cells of the feature it fills in each tile, in that tile's numbering.
        """
        found: dict[int, list[int]] = {}
        for cell in cells:
            if cell in self.inside:
                found.setdefault(self.owners[cell], []).append(self.places[cell])
        return found

"""The grid a feature is searched over, and which of its cells it really covers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from analysis.utils.maths import mask as packing


@dataclass(frozen=True, slots=True)
class Grid:
    """One feature's grid, and what a window over it is measured against.

    Attributes:
        cells: How many cells the grid holds.
        area_km2: How much ground the feature really has inside it.
        cell_km2: How much ground one cell of the grid covers.
        inside: Which cells of the grid the feature really covers.
    """

    cells: int
    area_km2: float
    cell_km2: float
    inside: frozenset[int]

    @classmethod
    def over(cls, side: int, cell_km2: float, grid_mask: bytes) -> Grid:
        """Lay the grid the coverage was measured on back over its feature.

        Args:
            side: How many cells the feature's grid holds along each axis.
            cell_km2: How much ground one cell of that grid covers.
            grid_mask: Which cells of it fall inside the feature.

        Returns:
            The grid, measuring the ground the feature really covers.
        """
        inside = packing.cells_of(grid_mask).tolist()
        return cls(
            cells=side * side,
            area_km2=len(inside) * cell_km2,
            cell_km2=cell_km2,
            inside=frozenset(inside),
        )

    def held_cells(self, cells: Sequence[int]) -> list[int]:
        """Keep the cells one footprint fills that the feature really covers.

        Args:
            cells: The cells of the feature's grid the footprint fills.

        Returns:
            The cells of the feature it fills, in the grid's own numbering.
        """
        return [cell for cell in cells if cell in self.inside]

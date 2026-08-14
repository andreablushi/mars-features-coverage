"""A grid of tiles laid over one feature, so a union stays local to a tile.

A single accumulated union grows with everything ever added to it, so every
later footprint pays for ground nowhere near itself. Tiling means a footprint
only meets the observations sharing its ground. The tiles are disjoint and cover
the feature, so summing their areas is exact: only the bookkeeping is
partitioned, never the geometry.

This module owns the grid alone. The accumulation inside a tile is in union.py.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import numpy as np
from shapely import STRtree, area, box, intersection, is_empty
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.computation.region import FeatureRegion


class TileGrid:
    """A grid of disjoint tiles covering one feature, and what reaches them.

    Attributes:
        caps: The ground in square metres each tile could ever hold, being its
            own overlap with the feature.
    """

    def __init__(
        self,
        region: FeatureRegion,
        shapes: Sequence[BaseGeometry],
        tiles: int = configs.UNION_TILES,
    ) -> None:
        """Lay a tile grid over one feature and index the shapes against it.

        Args:
            region: The projected feature the tiles cover.
            shapes: The projected footprints to be indexed, in the order their
                observations are to be walked.
            tiles: How many tiles to use along each axis.

        Returns:
            None.
        """
        min_x, min_y, max_x, max_y = region.shape.bounds
        step_x, step_y = (max_x - min_x) / tiles, (max_y - min_y) / tiles
        self._shapes = np.asarray(shapes, dtype=object)
        self._rectangles = np.asarray(
            [
                box(
                    min_x + column * step_x,
                    min_y + row * step_y,
                    min_x + (column + 1) * step_x,
                    min_y + (row + 1) * step_y,
                )
                for row in range(tiles)
                for column in range(tiles)
            ],
            dtype=object,
        )
        self.caps = area(intersection(self._rectangles, region.shape))
        self._index = STRtree(self._shapes)

    def __iter__(self) -> Iterator[tuple[BaseGeometry, float, np.ndarray]]:
        """Walk the tiles that can hold ground, with what reaches each one.

        A tile outside the feature is left out, since nothing drawn over it
        could ever be counted.

        Yields:
            Each tile's rectangle, the ground in square metres it could hold,
            and the indices of the shapes reaching it, in their original order.
        """
        for rectangle, cap in zip(self._rectangles, self.caps, strict=True):
            if cap <= 0.0:
                continue
            reaching = np.sort(self._index.query(rectangle))
            if reaching.size:
                yield rectangle, float(cap), reaching

    def clip(
        self, reaching: np.ndarray, rectangle: BaseGeometry
    ) -> tuple[np.ndarray, np.ndarray]:
        """Cut the given shapes to one tile, dropping the ones that miss it.

        The index answers on bounding boxes, so a shape it reports may still not
        reach the tile. Cutting settles that, for the whole chunk at once.

        Args:
            reaching: The indices of the shapes to cut.
            rectangle: The tile to cut them to.

        Returns:
            The kept indices and their clipped shapes, as a pair of arrays.
        """
        pieces = intersection(self._shapes[reaching], rectangle)
        kept = ~is_empty(pieces)
        return reaching[kept], pieces[kept]

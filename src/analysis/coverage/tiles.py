"""A grid of tiles laid over one feature, so a union stays local to a tile."""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence

import numpy as np
from shapely import STRtree, area, bounds, box, intersection, is_empty
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.geometry.region import FeatureRegion


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
        tiles: int | None = None,
    ) -> None:
        """Lay a tile grid over one feature and index the shapes against it.

        Args:
            region: The projected feature the tiles cover.
            shapes: The projected footprints to be indexed, in the order their
                observations are to be walked.
            tiles: How many tiles to use along each axis, or None to size the
                grid to the footprints.

        Returns:
            None.
        """
        min_x, min_y, max_x, max_y = region.shape.bounds
        if tiles is None:
            tiles = _tiles_per_axis(max_x - min_x, max_y - min_y, shapes)
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


def _tiles_per_axis(width: float, height: float, shapes: Sequence[BaseGeometry]) -> int:
    """Choose how many tiles a feature needs along each axis.

    A tile much smaller than a footprint is the expensive mistake: the footprint
    is then cut against dozens of tiles that each hold a sliver of it. Matching
    the tile to the typical footprint keeps that to a handful.

    Args:
        width: The feature's projected width in metres.
        height: The feature's projected height in metres.
        shapes: The projected footprints the grid will hold.

    Returns:
        The tile count per axis, within the configured bounds.
    """
    boxes = bounds(np.asarray(shapes, dtype=object))
    spans = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    typical = (
        float(np.sqrt(np.median(spans[spans > 0.0]))) if (spans > 0.0).any() else 0.0
    )
    if typical <= 0.0:
        return configs.MAX_UNION_TILES
    wanted = round(math.sqrt(width * height) / typical)
    return int(min(max(wanted, configs.MIN_UNION_TILES), configs.MAX_UNION_TILES))

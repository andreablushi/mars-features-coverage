"""A grid of sectors laid over one feature, so a union stays local to a sector."""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence

import numpy as np
from shapely import STRtree, area, bounds, box, intersection, is_empty
from shapely.geometry.base import BaseGeometry

from analysis.coverage import configs
from analysis.coverage.geometry.region import FeatureRegion


class SectorGrid:
    """A grid of disjoint sectors covering one feature, and what reaches them.

    Attributes:
        caps: The ground in square metres each sector could ever hold.
    """

    def __init__(
        self,
        region: FeatureRegion,
        shapes: Sequence[BaseGeometry],
        sectors: int | None = None,
    ) -> None:
        """Lay a sector grid over one feature and index the shapes against it.

        Args:
            region: The projected feature the sectors cover.
            shapes: The projected footprints to index, in the order they are walked.
            sectors: The sectors per axis, or None to size the grid to the footprints.

        Returns:
            None.
        """
        min_x, min_y, max_x, max_y = region.shape.bounds
        if sectors is None:
            sectors = _sectors_per_axis(max_x - min_x, max_y - min_y, shapes)
        step_x, step_y = (max_x - min_x) / sectors, (max_y - min_y) / sectors
        self._shapes = np.asarray(shapes, dtype=object)
        self._rectangles = np.asarray(
            [
                box(
                    min_x + column * step_x,
                    min_y + row * step_y,
                    min_x + (column + 1) * step_x,
                    min_y + (row + 1) * step_y,
                )
                for row in range(sectors)
                for column in range(sectors)
            ],
            dtype=object,
        )
        self.caps = area(intersection(self._rectangles, region.shape))
        self._index = STRtree(self._shapes)

    def __iter__(self) -> Iterator[tuple[BaseGeometry, float, np.ndarray]]:
        """Walk the sectors that can hold ground, with what reaches each one.

        Yields:
            Each sector's rectangle, the ground it holds, and the shapes reaching it.
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
        """Cut the given shapes to one sector, dropping the ones that miss it.

        Args:
            reaching: The indices of the shapes to cut.
            rectangle: The sector to cut them to.

        Returns:
            The kept indices and their clipped shapes, as a pair of arrays.
        """
        pieces = intersection(self._shapes[reaching], rectangle)
        kept = ~is_empty(pieces)
        return reaching[kept], pieces[kept]


def _sectors_per_axis(
    width: float, height: float, shapes: Sequence[BaseGeometry]
) -> int:
    """Choose how many sectors a feature needs along each axis.

    Args:
        width: The feature's projected width in metres.
        height: The feature's projected height in metres.
        shapes: The projected footprints the grid will hold.

    Returns:
        The sector count per axis, within the configured bounds.
    """
    boxes = bounds(np.asarray(shapes, dtype=object))
    spans = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    typical = (
        float(np.sqrt(np.median(spans[spans > 0.0]))) if (spans > 0.0).any() else 0.0
    )
    if typical <= 0.0:
        return configs.MAX_UNION_SECTORS
    wanted = round(math.sqrt(width * height) / typical)
    return int(min(max(wanted, configs.MIN_UNION_SECTORS), configs.MAX_UNION_SECTORS))

"""A running union kept in tiles, so each insert stays local.

A single accumulated union grows with everything ever added to it, so every
later footprint pays for ground nowhere near itself. Splitting the feature into
a grid of tiles and keeping one union per tile means a footprint only ever
touches the few tiles it actually overlaps.

The tiles are disjoint and together they cover the feature, so the total area
is the sum of theirs. That makes this exact, not an approximation: a footprint
is cut along tile edges and every piece is still counted once, in full. Only
the bookkeeping is partitioned, never the geometry.
"""

from __future__ import annotations

from shapely import GeometryCollection, box, covers, prepare, union_all
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.computation.region import FeatureRegion


class TiledUnion:
    """A running union of covered ground, partitioned into tiles.

    Attributes:
        area_m2: The ground covered so far in square metres.
    """

    def __init__(self, region: FeatureRegion, tiles: int = configs.UNION_TILES) -> None:
        """Lay a tile grid over one feature.

        Args:
            region: The projected feature the tiles cover.
            tiles: How many tiles to use along each axis.

        Returns:
            None.
        """
        min_x, min_y, max_x, max_y = region.shape.bounds
        self._region = region.shape
        self._side = tiles
        self._origin = (min_x, min_y)
        self._step = ((max_x - min_x) / tiles, (max_y - min_y) / tiles)
        self._shapes: list[BaseGeometry | None] = [None] * (tiles * tiles)
        self._areas = [0.0] * (tiles * tiles)
        self._caps: list[float | None] = [None] * (tiles * tiles)
        self.area_m2 = 0.0

    @property
    def shape(self) -> BaseGeometry:
        """Return the union built so far, seams between tiles healed.

        Returns:
            The accumulated geometry, empty until something is added.
        """
        parts = [shape for shape in self._shapes if shape is not None]
        return union_all(parts) if parts else GeometryCollection()

    def add(self, shape: BaseGeometry) -> float:
        """Fold one footprint into the union.

        Args:
            shape: The projected footprint to add.

        Returns:
            The area in square metres the footprint covered that the union had
            not already reached.
        """
        if shape.is_empty:
            return 0.0
        fresh = 0.0
        for index, tile in self._touched(shape):
            if self._areas[index] >= self._cap(index, tile):
                continue
            piece = shape.intersection(tile)
            if piece.is_empty:
                continue
            fresh += self._merge(index, piece)
        self.area_m2 += fresh
        return fresh

    def _merge(self, index: int, piece: BaseGeometry) -> float:
        """Fold one clipped piece into the tile that holds it.

        Args:
            index: The tile the piece belongs to.
            piece: The footprint clipped to that tile.

        Returns:
            The area the piece added to the tile.
        """
        current = self._shapes[index]
        if current is not None and covers(current, piece):
            return 0.0
        merged = piece if current is None else union_all([current, piece])
        prepare(merged)
        grown = merged.area
        added = max(grown - self._areas[index], 0.0)
        self._shapes[index] = merged
        self._areas[index] = grown
        return added

    def _touched(self, shape: BaseGeometry):
        """Yield the tiles a footprint's extent reaches.

        Args:
            shape: The projected footprint.

        Yields:
            Each overlapping tile's index and its rectangle.
        """
        min_x, min_y, max_x, max_y = shape.bounds
        first_column, last_column = self._span(min_x, max_x, 0)
        first_row, last_row = self._span(min_y, max_y, 1)
        for row in range(first_row, last_row + 1):
            for column in range(first_column, last_column + 1):
                yield row * self._side + column, self._tile(row, column)

    def _span(self, low: float, high: float, axis: int) -> tuple[int, int]:
        """Return the tile indices an extent spans along one axis.

        Args:
            low: The lower bound in projected metres.
            high: The upper bound in projected metres.
            axis: 0 for columns, 1 for rows.

        Returns:
            The first and last tile index, clamped to the grid.
        """
        origin, step = self._origin[axis], self._step[axis]
        last = self._side - 1
        first_index = min(max(int((low - origin) / step), 0), last)
        last_index = min(max(int((high - origin) / step), 0), last)
        return first_index, last_index

    def _tile(self, row: int, column: int) -> BaseGeometry:
        """Return one tile's rectangle.

        Args:
            row: The tile row.
            column: The tile column.

        Returns:
            The tile as a rectangle in projected metres.
        """
        origin_x, origin_y = self._origin
        step_x, step_y = self._step
        return box(
            origin_x + column * step_x,
            origin_y + row * step_y,
            origin_x + (column + 1) * step_x,
            origin_y + (row + 1) * step_y,
        )

    def _cap(self, index: int, tile: BaseGeometry) -> float:
        """Return the most ground a tile could ever hold.

        Footprints arrive already cut to the feature, so a tile can never fill
        beyond its own overlap with it. Once it reaches that, nothing more can
        be added and the tile is skipped outright.

        Args:
            index: The tile being asked about.
            tile: That tile's rectangle.

        Returns:
            The tile's coverable area in square metres.
        """
        if self._caps[index] is None:
            self._caps[index] = tile.intersection(self._region).area
        return self._caps[index]

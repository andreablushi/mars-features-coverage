"""How much new ground each observation covers, accumulated tile by tile.

A tile's union is rebuilt from scratch every UNION_CHUNK observations, never
grown one footprint at a time: each overlay inherits the last one's rounding and
adds its own, so a running union runs away, reaching 402,563 vertices on one
CRISM tile where the same ground needs 1,885.

Only whole footprints are ever unioned, never the residuals and never a filtered
subset, both of which leave gaps a later footprint rediscovers and counts twice.
Within a chunk each footprint is cut back against what is already covered, and
the area of what survives is its own new ground.
"""

from __future__ import annotations

import numpy as np
from shapely import area, covers, difference, prepare, union_all
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.computation.tiles import TileGrid


def accumulate(grid: TileGrid, count: int) -> np.ndarray:
    """Measure the new ground every observation covers.

    Args:
        grid: The tile grid holding the projected footprints.
        count: How many observations the grid was built over.

    Returns:
        The ground in square metres each observation covered that nothing
        before it had reached, indexed as the observations were given.
    """
    fresh = np.zeros(count, dtype=float)
    for rectangle, cap, reaching in grid:
        _fill_tile(grid, rectangle, cap, reaching, fresh)
    return fresh


def _fill_tile(
    grid: TileGrid,
    rectangle: BaseGeometry,
    cap: float,
    reaching: np.ndarray,
    fresh: np.ndarray,
) -> None:
    """Accumulate one tile, adding what it contributes to every observation.

    Args:
        grid: The tile grid, used to cut a chunk down to this tile.
        rectangle: The tile being accumulated.
        cap: The ground in square metres the tile could ever hold.
        reaching: The indices of the observations reaching it, in order.
        fresh: The per-observation totals to add this tile's share to.

    Returns:
        None.
    """
    covered: BaseGeometry | None = None
    arrived: list[BaseGeometry] = []
    limit = cap * (1.0 - configs.SATURATION_TOLERANCE)
    for start in range(0, reaching.size, configs.UNION_CHUNK):
        chunk = reaching[start : start + configs.UNION_CHUNK]
        indices, pieces = grid.clip(chunk, rectangle)
        if not indices.size:
            continue
        _measure(indices, pieces, covered, fresh)
        arrived.extend(pieces)
        covered = union_all(arrived)
        prepare(covered)
        if covered.area >= limit:
            return


def _measure(
    indices: np.ndarray,
    pieces: np.ndarray,
    covered: BaseGeometry | None,
    fresh: np.ndarray,
) -> None:
    """Record what each footprint in one chunk newly covers.

    A well imaged feature is mostly re-observation, so asking the prepared union
    whether it already holds a footprint is an indexed lookup where cutting the
    footprint against it is a full overlay.

    Args:
        indices: The observation index of every piece, in order.
        pieces: The footprints clipped to the tile, in the same order.
        covered: The tile's union of everything before this chunk, or None when
            the chunk is the first to reach the tile.
        fresh: The per-observation totals to add each residual's area to.

    Returns:
        None.
    """
    within: BaseGeometry | None = None
    for index, piece in zip(indices, pieces, strict=True):
        if covered is not None and covers(covered, piece):
            continue
        residual = piece if covered is None else difference(piece, covered)
        if residual.is_empty:
            continue
        if within is not None:
            residual = difference(residual, within)
            if residual.is_empty:
                continue
        fresh[index] += area(residual)
        within = residual if within is None else union_all([within, residual])

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

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from shapely import area, covers, difference, prepare, to_wkb, union_all
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.computation.region import FeatureRegion
from analysis.computation.tiles import TileGrid


def accumulate(region: FeatureRegion, shapes: Sequence[BaseGeometry]) -> np.ndarray:
    """Measure the new ground every observation covers.

    Args:
        region: The projected feature the footprints are cut to.
        shapes: The projected footprints, in chronological order.

    Returns:
        The ground in square metres each observation covered that nothing
        before it had reached, indexed as the observations were given.
    """
    fresh = np.zeros(len(shapes), dtype=float)
    first = _first_occurrences(shapes)
    grid = TileGrid(region, [shapes[index] for index in first])
    counted = np.zeros(first.size, dtype=float)
    with ThreadPoolExecutor(max_workers=configs.UNION_THREADS) as pool:
        for share in pool.map(lambda tile: _fill_tile(grid, *tile), grid):
            for index, added in share:
                counted[index] += added
    fresh[first] = counted
    return fresh


def _first_occurrences(shapes: Sequence[BaseGeometry]) -> np.ndarray:
    """Return where each distinct footprint is first seen.

    ODE publishes one record per data product rather than per observation, so
    a CRISM acquisition arrives three times over with the same footprint. A
    repeat of a footprint already seen covers no ground the first did not, and
    that holds exactly rather than to within rounding, so the repeats are left
    out of the union entirely and keep their zero.

    Args:
        shapes: The projected footprints, in chronological order.

    Returns:
        The ascending indices of the footprints worth accumulating.
    """
    seen: set[bytes] = set()
    first = []
    for index, blob in enumerate(to_wkb(np.asarray(shapes, dtype=object))):
        if blob not in seen:
            seen.add(blob)
            first.append(index)
    return np.asarray(first, dtype=int)


def _fill_tile(
    grid: TileGrid,
    rectangle: BaseGeometry,
    cap: float,
    reaching: np.ndarray,
) -> list[tuple[int, float]]:
    """Accumulate one tile and report what it contributes to each observation.

    The share is returned rather than written, because tiles are accumulated
    concurrently and one observation is reached by several of them.

    Args:
        grid: The tile grid, used to cut a chunk down to this tile.
        rectangle: The tile being accumulated.
        cap: The ground in square metres the tile could ever hold.
        reaching: The indices of the observations reaching it, in order.

    Returns:
        The ground in square metres this tile saw each observation cover first,
        as observation index and area pairs.
    """
    covered: BaseGeometry | None = None
    arrived: list[BaseGeometry] = []
    share: list[tuple[int, float]] = []
    limit = cap * (1.0 - configs.SATURATION_TOLERANCE)
    for start in range(0, reaching.size, configs.UNION_CHUNK):
        chunk = reaching[start : start + configs.UNION_CHUNK]
        indices, pieces = grid.clip(chunk, rectangle)
        if not indices.size:
            continue
        _measure(indices, pieces, covered, share)
        arrived.extend(pieces)
        covered = union_all(arrived)
        prepare(covered)
        if covered.area >= limit:
            break
    return share


def _measure(
    indices: np.ndarray,
    pieces: np.ndarray,
    covered: BaseGeometry | None,
    share: list[tuple[int, float]],
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
        share: The tile's contributions so far, appended to in place.

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
        share.append((int(index), area(residual)))
        within = residual if within is None else union_all([within, residual])

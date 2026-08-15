"""How much new ground each observation covers, accumulated tile by tile."""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from shapely import area, covers, prepare, to_wkb, union_all
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

from analysis import configs
from analysis.coverage.tiles import TileGrid
from analysis.geometry.region import FeatureRegion


def _robust(operation, *shapes):
    """Run an overlay, retrying on a fine grid when exact arithmetic fails.

    GEOS nodes overlays in floating point and occasionally cannot resolve a
    near-degenerate crossing, raising rather than returning a wrong answer.
    Snapping to SNAP_GRID_M resolves it, and at a micron on ground measured in
    kilometres the shift is far below anything the footprints themselves claim.

    Args:
        operation: The shapely overlay to run.
        shapes: Its operands.

    Returns:
        The overlay's result.
    """
    try:
        return operation(*shapes)
    except GEOSException:
        return operation(*shapes, grid_size=configs.SNAP_GRID_M)


def new_ground(region: FeatureRegion, shapes: Sequence[BaseGeometry]) -> np.ndarray:
    """Measure the new ground every observation covers.

    Args:
        region: The projected feature the footprints are cut to.
        shapes: The projected footprints, in chronological order.

    Returns:
        The ground in square metres each observation covered that nothing
        before it had reached, indexed as the observations were given.
    """
    fresh = np.zeros(len(shapes), dtype=float)
    first = _distinct_footprints(shapes)
    grid = TileGrid(region, [shapes[index] for index in first])
    counted = np.zeros(first.size, dtype=float)
    with ThreadPoolExecutor(max_workers=configs.UNION_THREADS) as pool:
        for share in pool.map(lambda tile: _tile_contributions(grid, *tile), grid):
            for index, added in share:
                counted[index] += added
    fresh[first] = counted
    return fresh


def _distinct_footprints(shapes: Sequence[BaseGeometry]) -> np.ndarray:
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


def _tile_contributions(
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
        _record_first_cover(indices, pieces, covered, share)
        arrived.extend(pieces)
        covered = _robust(union_all, arrived)
        prepare(covered)
        if covered.area >= limit:
            break
    return share


def _record_first_cover(
    indices: np.ndarray,
    pieces: np.ndarray,
    covered: BaseGeometry | None,
    share: list[tuple[int, float]],
) -> None:
    """Record what each footprint in one chunk newly covers.

    What a footprint adds is read as the area its own union grows by, rather
    than as the area of the leftover cut off it. Both say the same thing in
    exact arithmetic, but a leftover is a shape that touches what produced it
    along its whole boundary, which is the case GEOS nodes worst: unioning one
    back in silently dropped most of a multipart leftover, and cutting against
    one raised outright on the larger features. A union of two footprints as
    they were published meets neither.

    A well imaged feature is mostly re-observation, so asking the prepared
    union whether it already holds a footprint is an indexed lookup where
    merging it in is a full overlay.

    That question is answered on the boundary though, and a footprint lying
    along the union's edge is reported as not covered while adding no ground
    at all. Merging one in welds its vertices into the edge it sits on, and a
    tile reached by hundreds of them grew past a million vertices while its
    area never moved, each union re-noding everything before it. So a merge
    that buys no ground is discarded and the union left as it was.

    Args:
        indices: The observation index of every piece, in order.
        pieces: The footprints clipped to the tile, in the same order.
        covered: The tile's union of everything before this chunk, or None when
            the chunk is the first to reach the tile.
        share: The tile's contributions so far, appended to in place.

    Returns:
        None.
    """
    running = covered
    for index, piece in zip(indices, pieces, strict=True):
        if running is None:
            share.append((int(index), area(piece)))
            running = piece
            prepare(running)
            continue
        if covers(running, piece):
            continue
        merged = _robust(union_all, [running, piece])
        added = merged.area - running.area
        if added <= running.area * configs.SATURATION_TOLERANCE:
            continue
        share.append((int(index), added))
        running = merged
        prepare(running)

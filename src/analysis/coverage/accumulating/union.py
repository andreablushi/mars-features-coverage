"""How much new ground each observation covers, accumulated sector by sector."""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from shapely import area, covers, prepare, union_all
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

from analysis.coverage import configs
from analysis.coverage.geometry.region import FeatureRegion
from analysis.coverage.geometry.sectors import SectorGrid


def _robust(operation, *shapes):
    """Run an overlay, retrying on a fine grid when exact arithmetic fails.

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
        The ground in square metres each observation covered first, as it was given.
    """
    grid = SectorGrid(region, shapes)
    fresh = np.zeros(len(shapes), dtype=float)
    with ThreadPoolExecutor(max_workers=configs.UNION_THREADS) as pool:
        for share in pool.map(
            lambda sector: _sector_contributions(grid, *sector), grid
        ):
            for index, added in share:
                fresh[index] += added
    return fresh


def _sector_contributions(
    grid: SectorGrid,
    rectangle: BaseGeometry,
    cap: float,
    reaching: np.ndarray,
) -> list[tuple[int, float]]:
    """Accumulate one sector and report what it contributes to each observation.

    Args:
        grid: The sector grid, used to cut a chunk down to this sector.
        rectangle: The sector being accumulated.
        cap: The ground in square metres the sector could ever hold.
        reaching: The indices of the observations reaching it, in order.

    Returns:
        The ground in square metres this sector saw each observation cover first.
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

    Args:
        indices: The observation index of every piece, in order.
        pieces: The footprints clipped to the sector, in the same order.
        covered: The sector's union before this chunk, or None when it is the first.
        share: The sector's contributions so far, appended to in place.

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

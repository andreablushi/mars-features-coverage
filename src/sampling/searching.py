"""Searching every tile of one feature for the window a dataset would keep."""

from __future__ import annotations

from collections.abc import Sequence

from coverage.results import SetCoverage
from sampling.models.study import Study
from selector import algorithm
from selector.models import track as timeline
from selector.models.strategy import Strategy
from selector.models.tiles import Grid
from selector.utils import constraints, tiling


def study(coverage: Sequence[SetCoverage], strategy: Strategy) -> Study:
    """Search every tile of a feature under one strategy.

    Args:
        coverage: The feature's instrument sets, in any order.
        strategy: Which instruments a window has to hold, and how much ground each.

    Returns:
        What the search found, every tile it ran over and the window each earned.
    """
    summary = coverage[0].summary
    if not summary.mask_cells:
        return Study(
            strategy,
            Grid(
                tiles=[],
                across=0,
                owners=[],
                places=[],
                cell_km2=0.0,
                inside=frozenset(),
            ),
            [],
            [],
        )
    grid = tiling.split(
        summary.grid_side,
        strategy.tile_km,
        summary.cell_km2,
        summary.grid_mask,
    )
    # The one place the strategy is read, which everything below takes it from
    settled = constraints.read(strategy, coverage, grid)
    tracks = timeline.build(coverage, grid, settled)
    return Study(
        strategy=settled,
        grid=grid,
        tracks=tracks,
        surveys=[algorithm.search(track, settled) for track in tracks],
    )

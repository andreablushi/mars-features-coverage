"""Searching one whole feature for the window a dataset would keep."""

from __future__ import annotations

from collections.abc import Sequence

from analysis.coverage.models.coverage import SetCoverage
from analysis.sampling.models.study import Study
from analysis.selector import algorithm
from analysis.selector.models import track as timeline
from analysis.selector.models.filter import Filter
from analysis.selector.models.grid import Grid
from analysis.selector.utils.feature_filter import read_feature_filter
from analysis.utils.maths import mask as packing


def study_feature(coverage: Sequence[SetCoverage], criteria: Filter) -> Study:
    """Search one feature under the filter.

    Args:
        coverage: The feature's instrument sets, in any order.
        criteria: Which instruments a window has to hold, and how much ground each.

    Returns:
        What the search found, the timeline it ran over and the window it earned.
    """
    summary = coverage[0].summary
    inside = packing.cells_of(summary.grid_mask).tolist()
    grid = Grid(
        cells=summary.grid_side * summary.grid_side,
        area_km2=len(inside) * summary.cell_km2,
        cell_km2=summary.cell_km2,
        inside=frozenset(inside),
    )
    # The one place the filter is read, which everything below takes it from
    settled = read_feature_filter(criteria, coverage, grid)
    track = timeline.build(coverage, grid, settled)
    return Study(
        criteria=settled,
        track=track,
        survey=algorithm.search(track, settled) if track else None,
    )

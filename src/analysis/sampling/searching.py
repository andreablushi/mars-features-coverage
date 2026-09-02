"""Searching one whole feature for the window a dataset would keep."""

from __future__ import annotations

from collections.abc import Sequence

from analysis.coverage.results import SetCoverage
from analysis.sampling.models.study import Study
from analysis.selector import algorithm
from analysis.selector.models import track as timeline
from analysis.selector.models.filter import Filter
from analysis.selector.models.grid import Grid
from analysis.selector.utils import constraints

_NOTHING_MEASURED = Grid(cells=0, area_km2=0.0, cell_km2=0.0, inside=frozenset())


def study_feature(coverage: Sequence[SetCoverage], criteria: Filter) -> Study:
    """Search one feature under the filter.

    Args:
        coverage: The feature's instrument sets, in any order.
        criteria: Which instruments a window has to hold, and how much ground each.

    Returns:
        What the search found, the timeline it ran over and the window it earned.
    """
    summary = coverage[0].summary
    if not summary.mask_cells:
        return Study(criteria, _NOTHING_MEASURED, None, None)
    grid = Grid.over(summary.grid_side, summary.cell_km2, summary.grid_mask)
    # The one place the filter is read, which everything below takes it from
    settled = constraints.read(criteria, coverage, grid)
    track = timeline.build(coverage, grid, settled)
    return Study(
        criteria=settled,
        grid=grid,
        track=track,
        survey=algorithm.search(track, settled) if track else None,
    )

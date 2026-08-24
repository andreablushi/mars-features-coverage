"""Searching every tile of one feature for the window a dataset would keep."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import SetCoverage
from survey import algorithm
from survey.models import track as timeline
from survey.models.strategy import Strategy
from survey.models.study import Study
from survey.models.tiles import Patchwork
from survey.utils import tiling


def study(coverage: Sequence[SetCoverage], strategy: Strategy) -> Study:
    """Search every tile of a feature under one strategy.

    Args:
        coverage: The feature's instrument sets, in any order.
        strategy: Which instruments a window has to hold and how much ground
            each of them has to reach.

    Returns:
        What the search found, holding every tile it ran over and the window
        each of them earned.
    """
    summary = coverage[0].summary
    if not summary.mask_cells:
        return Study(strategy, _ungridded(), [], [])
    patchwork = tiling.split(
        summary.grid_side,
        strategy.tile_km,
        summary.cell_km2,
        summary.grid_mask,
    )
    tracks = timeline.build(coverage, patchwork, strategy.admits)
    return Study(
        strategy=strategy,
        patchwork=patchwork,
        tracks=tracks,
        surveys=[algorithm.search(track, strategy) for track in tracks],
    )


def _ungridded() -> Patchwork:
    """Build the tiling of a feature no instrument set ever filled a cell of.

    Returns:
        A patchwork holding no tile at all.
    """
    return Patchwork(tiles=[], across=0, owners=[], places=[], cell_km2=0.0)

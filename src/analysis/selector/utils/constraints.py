"""Reading one strategy against one feature, once, into what the feature is asked."""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Sequence

from analysis.coverage.results import SetCoverage
from analysis.selector.models.grid import Grid
from analysis.selector.models.strategy import Constraints, Strategy
from analysis.utils.maths import ground


def read(strategy: Strategy, coverage: Sequence[SetCoverage], grid: Grid) -> Strategy:
    """Settle everything a strategy asks of a feature.

    This is the only place a strategy is read. What it works out is held on the
    strategy it hands back, so the search and the admission both take what they
    need off that rather than working it out again.

    Args:
        strategy: What the instruments are asked for, and which of them are timeless.
        coverage: The feature's instrument sets, in any order.
        grid: The grid the feature is searched over.

    Returns:
        The same strategy, carrying what it asks of the feature.
    """
    iids = [instrument.summary.iid for instrument in coverage]
    windowed, standing = _asked(strategy, iids, grid.area_km2, grid.cell_km2)
    return dataclasses.replace(
        strategy,
        least=_least(coverage, grid, strategy.admits),
        windowed=windowed,
        standing=standing,
    )


def _asked(
    strategy: Strategy, iids: Sequence[str], area_km2: float, cell_km2: float
) -> tuple[Constraints, Constraints]:
    """Read what a strategy asks into the sets and the cells of one feature.

    Args:
        strategy: What the instruments are asked for, and which of them are timeless.
        iids: The instrument each set on the timeline belongs to, in order.
        area_km2: How much ground the feature covers.
        cell_km2: How much ground one cell of that ground covers.

    Returns:
        What a window is scored on and what the record answers for, tightest first.
    """
    windowed: Constraints = []
    standing: Constraints = []
    for constraint in strategy.constraints:
        answers = [
            (
                tuple(index for index, owner in enumerate(iids) if owner == iid),
                max(1, math.ceil(ground.cells(share, area_km2, cell_km2))),
            )
            for iid, share in constraint.items()
        ]
        # A constraint is out of the window only when everything answering it is
        held = (
            standing
            if all(iid in strategy.timeless for iid in constraint)
            else windowed
        )
        held.append(answers)
    return (
        sorted(windowed, key=lambda answers: -min(floor for _, floor in answers)),
        sorted(standing, key=lambda answers: -min(floor for _, floor in answers)),
    )


def _least(
    coverage: Sequence[SetCoverage], grid: Grid, admits: dict[str, float]
) -> list[float]:
    """Work out the pixels each set has to land on the feature to be a look at it.

    An instrument's whole-grid bar is scaled down by the ground the feature
    actually holds in it, along one axis for a sounder and over both for an imager.

    Args:
        coverage: The feature's instrument sets, in any order.
        grid: The grid the feature is searched over.
        admits: The pixels each instrument has to land on a whole feature, by iid.

    Returns:
        The pixels each set has to land, by set, in the order the coverage names them.
    """
    iids = [instrument.summary.iid for instrument in coverage]
    # A set publishing a swath width is a sounder, whose pixels lie along a line
    linear = [
        any(observation.width_km is not None for observation in instrument.events)
        for instrument in coverage
    ]
    covered = grid.area_km2 / (grid.cells * grid.cell_km2)
    return [
        admits.get(iid, 0.0) * (math.sqrt(covered) if along_track else covered)
        for iid, along_track in zip(iids, linear, strict=True)
    ]

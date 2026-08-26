"""What one strategy asks of one tile, in the sets, cells and pixels it counts in."""

from __future__ import annotations

import math
from collections.abc import Sequence

from models.results import SetCoverage
from survey.models.strategy import Strategy
from survey.models.tiles import Patchwork
from utils.maths import ground

# One instrument answering a constraint: the sets that speak for it and its floor
Answer = tuple[tuple[int, ...], int]
# A constraint any one of its instruments can answer, and what a window is asked.
Constraints = list[list[Answer]]


def read_strategy(
    strategy: Strategy, iids: Sequence[str], area_km2: float, cell_km2: float
) -> tuple[Constraints, Constraints]:
    """Read what a strategy asks for into the sets and the cells of one tile.

    Args:
        strategy: What the instruments are asked for, and which of them are timeless.
        iids: The instrument each set on the timeline belongs to, in order.
        area_km2: How much ground the search is run over.
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


def least_pixels(
    coverage: Sequence[SetCoverage], patchwork: Patchwork, admits: dict[str, float]
) -> list[list[float]]:
    """Work out the pixels each set has to land on each tile to be a look at it.

    An instrument's whole-tile bar is scaled down to each tile by the ground that
    tile actually holds, along one axis for a sounder and over both for an imager.

    Args:
        coverage: The feature's instrument sets, in any order.
        patchwork: The feature cut into tiles.
        admits: The pixels each instrument has to land on a whole tile, by iid.

    Returns:
        The pixels each set has to land, by tile and then by set, in patchwork order.
    """
    iids = [instrument.summary.iid for instrument in coverage]
    # A set publishing a swath width is a sounder, whose pixels lie along a line
    linear = [
        any(observation.width_km is not None for observation in instrument.events)
        for instrument in coverage
    ]
    least: list[list[float]] = []
    for patch in patchwork.tiles:
        covered = patch.area_km2 / (patch.cells * patchwork.cell_km2)
        least.append(
            [
                admits.get(iid, 0.0) * (math.sqrt(covered) if along_track else covered)
                for iid, along_track in zip(iids, linear, strict=True)
            ]
        )
    return least

"""Which observations are a look at the feature rather than a clip of its edge."""

from __future__ import annotations

from collections.abc import Sequence

from analysis.coverage.results import Event, SetCoverage
from analysis.selector.models.grid import Grid
from analysis.selector.models.strategy import Strategy
from analysis.utils.maths import mask as packing

# The admitted observations, the set each belongs to, and the cells each fills
Held = list[tuple[Event, int, list[int]]]


def admit_observation(
    coverage: Sequence[SetCoverage], grid: Grid, strategy: Strategy
) -> tuple[Held, Held]:
    """Keep every observation big enough for the feature, and turn the rest away.

    Args:
        coverage: The feature's instrument sets, in any order.
        grid: The grid the feature is searched over.
        strategy: The strategy read against the feature, holding the pixel floors.

    Returns:
        What the feature keeps and what it turned away, both carrying the set
        each observation belongs to and the cells it fills.
    """
    held: Held = []
    refused: Held = []
    least = strategy.least
    for owner, instrument in enumerate(coverage):
        for observation in instrument.events:
            spread, pixels = observation.own_km2, observation.pixels
            cells = grid.held_cells(packing.cells_of(observation.mask).tolist())
            if not cells:
                continue
            landed = (
                pixels * len(cells) * grid.cell_km2 / spread
                if spread and pixels is not None
                else 0.0
            )
            taken = held if landed >= least[owner] else refused
            taken.append((observation, owner, cells))
    return held, refused

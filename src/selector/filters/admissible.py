"""Which observations are a look at the tile rather than a clip of its edge."""

from __future__ import annotations

from collections.abc import Sequence

from coverage.results import Event, SetCoverage
from selector.models.strategy import Strategy
from selector.models.tiles import Grid
from utils.maths import mask as packing

# One tile's admitted observations, the set each belongs to, and the cells it fills
Held = list[tuple[Event, int, list[int]]]


def admit_observation(
    coverage: Sequence[SetCoverage], grid: Grid, strategy: Strategy
) -> tuple[list[Held], list[Held]]:
    """Keep every observation big enough for its tile, and turn the rest away.

    Args:
        coverage: The feature's instrument sets, in any order.
        grid: The feature cut into tiles.
        strategy: The strategy read against the feature, holding the pixel floors.

    Returns:
        What each tile keeps and what it turned away, both in grid order and
        both carrying the set each observation belongs to and the cells it fills.
    """
    held: list[Held] = [[] for _ in grid.tiles]
    refused: list[Held] = [[] for _ in grid.tiles]
    least = strategy.least
    for owner, instrument in enumerate(coverage):
        for observation in instrument.events:
            spread, pixels = observation.own_km2, observation.pixels
            filled = packing.cells_of(observation.mask).tolist()
            for tile, cells in grid.scatter_cells(filled).items():
                landed = (
                    pixels * len(cells) * grid.cell_km2 / spread
                    if spread and pixels is not None
                    else 0.0
                )
                if landed >= least[tile][owner]:
                    held[tile].append((observation, owner, cells))
                else:
                    refused[tile].append((observation, owner, cells))
    return held, refused

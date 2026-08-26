"""Which observations are a look at the tile rather than a clip of its edge."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import Event, SetCoverage
from survey.models.tiles import Patchwork
from survey.utils import constraints
from utils.maths import mask as packing

# One tile's admitted observations, the set each belongs to, and the cells it fills
Held = list[tuple[Event, int, list[int]]]


def admit_observation(
    coverage: Sequence[SetCoverage], patchwork: Patchwork, admits: dict[str, float]
) -> tuple[list[Held], list[list[Event]]]:
    """Keep every observation big enough for its tile, and turn the rest away.

    An observation covering no ground, or publishing no pixel count, lands nothing
    on the tile and is turned away.

    Args:
        coverage: The feature's instrument sets, in any order.
        patchwork: The feature cut into tiles.
        admits: The pixels each instrument has to land on a whole tile, by iid.

    Returns:
        What each tile keeps and what it turned away, both in patchwork order.
    """
    held: list[Held] = [[] for _ in patchwork.tiles]
    refused: list[list[Event]] = [[] for _ in patchwork.tiles]
    # What each set has to land on each tile, worked out once for the feature
    least = constraints.least_pixels(coverage, patchwork, admits)
    for owner, instrument in enumerate(coverage):
        for observation in instrument.events:
            spread, pixels = observation.own_km2, observation.pixels
            filled = packing.cells_of(observation.mask).tolist()
            for tile, cells in patchwork.scatter_cells(filled).items():
                landed = (
                    pixels * len(cells) * patchwork.cell_km2 / spread
                    if spread and pixels is not None
                    else 0.0
                )
                if landed >= least[tile][owner]:
                    held[tile].append((observation, owner, cells))
                else:
                    refused[tile].append(observation)
    return held, refused

"""Every instrument's observations of one tile, merged onto one time axis."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from coverage.results import Event, SetCoverage
from selector import configs
from selector.filters import admissible
from selector.models.strategy import Strategy
from selector.models.tiles import Grid


@dataclass(frozen=True, slots=True)
class Track:
    """One tile's observations, from every instrument set, in time order.

    Attributes:
        tile: Which tile of the feature the observations were cut to.
        observations: The observations the search may pick from, oldest first.
        times: When each of them started, in days, which is what a span is measured in.
        owners: The instrument set each belongs to, as its index into labels.
        cells: The tile's own cells each fills, in the same order, each named once.
        labels: The name of each set, in the order owners index them.
        iids: The instrument each set belongs to, in the same order.
        grid_cells: How many cells the tile holds.
        area_km2: How much ground the tile covers.
        cell_km2: How much ground one cell covers.
        refused: The observations left off the axis, each with the set it belongs
            to and the cells it fills, oldest first.
    """

    tile: int
    observations: list[Event]
    times: list[float]
    owners: list[int]
    cells: list[np.ndarray]
    labels: list[str]
    iids: list[str]
    grid_cells: int
    area_km2: float
    cell_km2: float
    refused: admissible.Held


def build(
    coverage: Sequence[SetCoverage], grid: Grid, strategy: Strategy
) -> list[Track]:
    """Merge a feature's instrument sets into one timeline per tile.

    Args:
        coverage: The feature's instrument sets, in any order.
        grid: The feature cut into tiles.
        strategy: The strategy read against the feature, read once.

    Returns:
        One timeline per tile holding anything measurable, in grid order.
    """
    held, refused = admissible.admit_observation(coverage, grid, strategy)
    labels = [instrument.label for instrument in coverage]
    iids = [instrument.summary.iid for instrument in coverage]
    return [
        _track(tile, grid, held[tile], refused[tile], labels, iids)
        for tile in range(len(grid.tiles))
        if held[tile]
    ]


def _track(
    tile: int,
    grid: Grid,
    held: admissible.Held,
    refused: admissible.Held,
    labels: list[str],
    iids: list[str],
) -> Track:
    """Lay one tile's observations out on a single time axis.

    Args:
        tile: Which tile of the feature they were cut to.
        grid: The feature cut into tiles.
        held: The observations the tile keeps, in no particular order.
        refused: The ones it turned away for being too small.
        labels: The name of every instrument set of the feature.
        iids: The instrument every one of them belongs to.

    Returns:
        The timeline.
    """
    held.sort(key=lambda item: item[0].t_start)
    patch = grid.tiles[tile]
    return Track(
        tile=tile,
        observations=[observation for observation, _, _ in held],
        times=[
            observation.t_start.timestamp() / configs.DAY_SECONDS
            for observation, _, _ in held
        ],
        owners=[owner for _, owner, _ in held],
        cells=[np.asarray(cells, dtype=np.intp) for _, _, cells in held],
        labels=labels,
        iids=iids,
        grid_cells=patch.cells,
        area_km2=patch.area_km2,
        cell_km2=grid.cell_km2,
        refused=sorted(refused, key=lambda item: item[0].t_start),
    )

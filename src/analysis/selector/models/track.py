"""Every instrument's observations of one feature, merged onto one time axis."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from analysis.coverage.results import Event, SetCoverage
from analysis.selector import configs
from analysis.selector.filters import admissible
from analysis.selector.models.filter import Filter
from analysis.selector.models.grid import Grid


@dataclass(frozen=True, slots=True)
class Track:
    """One feature's observations, from every instrument set, in time order.

    Attributes:
        observations: The observations the search may pick from, oldest first.
        times: When each of them started, in days, which is what a span is measured in.
        owners: The instrument set each belongs to, as its index into labels.
        cells: The feature's cells each fills, in the same order, each named once.
        labels: The name of each set, in the order owners index them.
        iids: The instrument each set belongs to, in the same order.
        grid_cells: How many cells the feature's grid holds.
        area_km2: How much ground the feature covers.
        cell_km2: How much ground one cell covers.
        refused: The observations left off the axis, each with the set it belongs
            to and the cells it fills, oldest first.
    """

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
    coverage: Sequence[SetCoverage], grid: Grid, criteria: Filter
) -> Track | None:
    """Merge a feature's instrument sets onto one timeline.

    Args:
        coverage: The feature's instrument sets, in any order.
        grid: The grid the feature is searched over.
        criteria: The filter read against the feature, read once.

    Returns:
        The timeline, or None when the feature holds nothing measurable.
    """
    held, refused = admissible.admit_observation(coverage, grid, criteria)
    if not held:
        return None
    held.sort(key=lambda item: item[0].t_start)
    return Track(
        observations=[observation for observation, _, _ in held],
        times=[
            observation.t_start.timestamp() / configs.DAY_SECONDS
            for observation, _, _ in held
        ],
        owners=[owner for _, owner, _ in held],
        cells=[np.asarray(cells, dtype=np.intp) for _, _, cells in held],
        labels=[instrument.label for instrument in coverage],
        iids=[instrument.summary.iid for instrument in coverage],
        grid_cells=grid.cells,
        area_km2=grid.area_km2,
        cell_km2=grid.cell_km2,
        refused=sorted(refused, key=lambda item: item[0].t_start),
    )

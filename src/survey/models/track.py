"""Every instrument's observations of one tile, merged onto one time axis."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from models.results import Event, SetCoverage
from survey import configs
from survey.filters import admissible
from survey.models.tiles import Patchwork


@dataclass(frozen=True, slots=True)
class Track:
    """One tile's observations, from every instrument set, in time order.

    Attributes:
        tile: Which tile of the feature the observations were cut to.
        observations: The observations the search may pick from, oldest first.
        times: When each of them started, in days, which is what a span is measured in.
        owners: The instrument set each belongs to, as its index into labels.
        cells: The tile's own cells each fills, in the same order.
        labels: The name of each set, in the order owners index them.
        iids: The instrument each set belongs to, in the same order.
        grid: How many cells the tile holds.
        area_km2: How much ground the tile covers.
        cell_km2: How much ground one cell covers.
        refused: The observations left off the axis, oldest first.
    """

    tile: int
    observations: list[Event]
    times: list[float]
    owners: list[int]
    cells: list[list[int]]
    labels: list[str]
    iids: list[str]
    grid: int
    area_km2: float
    cell_km2: float
    refused: list[Event]


def build(
    coverage: Sequence[SetCoverage], patchwork: Patchwork, admits: dict[str, float]
) -> list[Track]:
    """Merge a feature's instrument sets into one timeline per tile.

    Args:
        coverage: The feature's instrument sets, in any order.
        patchwork: The feature cut into tiles.
        admits: The pixels each instrument has to land on a whole tile.

    Returns:
        One timeline per tile holding anything measurable, in patchwork order.
    """
    held, refused = admissible.admit_observation(coverage, patchwork, admits)
    labels = [instrument.label for instrument in coverage]
    iids = [instrument.summary.iid for instrument in coverage]
    return [
        _track(tile, patchwork, held[tile], refused[tile], labels, iids)
        for tile in range(len(patchwork.tiles))
        if held[tile]
    ]


def _track(
    tile: int,
    patchwork: Patchwork,
    held: admissible.Held,
    refused: list[Event],
    labels: list[str],
    iids: list[str],
) -> Track:
    """Lay one tile's observations out on a single time axis.

    Args:
        tile: Which tile of the feature they were cut to.
        patchwork: The feature cut into tiles.
        held: The observations the tile keeps, in no particular order.
        refused: The ones it turned away for being too small.
        labels: The name of every instrument set of the feature.
        iids: The instrument every one of them belongs to.

    Returns:
        The timeline.
    """
    held.sort(key=lambda item: item[0].t_start)
    patch = patchwork.tiles[tile]
    return Track(
        tile=tile,
        observations=[observation for observation, _, _ in held],
        times=[
            observation.t_start.timestamp() / configs.DAY_SECONDS
            for observation, _, _ in held
        ],
        owners=[owner for _, owner, _ in held],
        cells=[cells for _, _, cells in held],
        labels=labels,
        iids=iids,
        grid=patch.cells,
        area_km2=patch.area_km2,
        cell_km2=patchwork.cell_km2,
        refused=sorted(refused, key=lambda observation: observation.t_start),
    )

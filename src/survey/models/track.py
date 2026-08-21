"""Every instrument's observations of one feature, merged onto one time axis."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from models.results import Event, SetCoverage
from survey import configs
from survey.filters import admissible
from utils.maths import mask as packing

Burned = list[tuple[Event, list[int]]]


@dataclass(frozen=True, slots=True)
class Track:
    """One feature's observations, from every instrument set, in time order.

    Attributes:
        observations: The observations the search may pick from, oldest first.
        times: When each of them started, in days, which is what a span is
            measured in.
        owners: The instrument set each belongs to, as its index into labels.
        cells: The feature's cells each fills, in the same order.
        sounder: Whether each is a sounder track, one of which a survey is
            required to hold.
        totals: How many cells each set fills across the whole record, which is
            what its reach inside a window is a share of.
        labels: The name of each set, in the order owners index them.
        grid: How many cells the feature's grid holds.
        refused: The observations left off the axis, oldest first, so that a
            window can say how many fell inside it.
    """

    observations: list[Event]
    times: list[float]
    owners: list[int]
    cells: list[list[int]]
    sounder: list[bool]
    totals: list[int]
    labels: list[str]
    grid: int
    refused: list[Event]


def build(coverage: Sequence[SetCoverage]) -> Track | None:
    """Merge a feature's instrument sets into one Track data type the search can walk.

    Args:
        coverage: The feature's instrument sets, in any order.

    Returns:
        The timeline, or None when no set left anything measurable behind.
    """
    sets: list[tuple[SetCoverage, Burned]] = []
    refused: list[Event] = []
    for instrument in coverage:
        width_km = math.sqrt(max(instrument.summary.feature_area_km2, 0.0))
        burned: Burned = []
        for observation in instrument.events:
            # Gather the cells the observation fills
            cells = packing.cells_of(observation.mask).tolist()
            # Filter out not admissible observations, and keep the rest
            if admissible.admissible(observation, cells, width_km):
                # Keep track for future cumulation and search
                burned.append((observation, cells))
            else:
                refused.append(observation)
        if burned:
            sets.append((instrument, burned))
    if not sets:
        return None
    # Merge the sets into one timeline
    merged = [
        (observation, filled, owner)
        for owner, (_, burned) in enumerate(sets)
        for observation, filled in burned
    ]
    merged.sort(key=lambda item: item[0].t_start)
    # Cumulate the total number of cells each set fills
    reached = max(max(filled) for _, burned in sets for _, filled in burned)
    return Track(
        observations=[observation for observation, _, _ in merged],
        times=[
            observation.t_start.timestamp() / configs.DAY_SECONDS
            for observation, _, _ in merged
        ],
        owners=[owner for _, _, owner in merged],
        cells=[filled for _, filled, _ in merged],
        sounder=[bool(observation.width_km) for observation, _, _ in merged],
        totals=[
            len({cell for _, filled in burned for cell in filled}) for _, burned in sets
        ],
        labels=[instrument.label for instrument, _ in sets],
        grid=max(coverage[0].summary.mask_cells, reached + 1),
        refused=sorted(refused, key=lambda observation: observation.t_start),
    )

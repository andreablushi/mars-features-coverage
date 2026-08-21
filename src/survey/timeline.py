"""Every instrument's observations of one feature, merged onto one time axis."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from models.results import Event, SetCoverage
from survey import configs, filtering
from utils import mask as packing

Burned = list[tuple[Event, list[int]]]


@dataclass(frozen=True, slots=True)
class Track:
    """One feature's observations, from every instrument set, in time order.

    Attributes:
        moments: When each observation started, oldest first.
        times: The same instants in days, which is what a span is measured in.
        owners: The instrument set each observation belongs to, as its index
            into labels.
        cells: The feature's cells each observation fills, in the same order.
        grounds: How much of the feature each observation covers, in square
            kilometres, in the same order.
        pixels: How many of the instrument's own pixels each of them landed
            inside the feature, in the same order.
        sounder: Whether each observation is a sounder track, one of which a
            survey is required to hold.
        totals: How many cells each set fills across the whole record, which is
            what its reach inside a window is a share of.
        labels: The name of each set, in the order owners index them.
        grid: How many cells the feature's grid holds.
        refused: When each observation left off the axis was taken, oldest
            first, so that a window can say how many fell inside it.
        sounded: How many of those were sounder tracks, which a survey
            cannot be found without.
    """

    moments: list[datetime]
    times: list[float]
    owners: list[int]
    cells: list[list[int]]
    grounds: list[float]
    pixels: list[float | None]
    sounder: list[bool]
    totals: list[int]
    labels: list[str]
    grid: int
    refused: list[datetime]
    sounded: int

    @property
    def size(self) -> int:
        """Return how many observations the timeline holds.

        Returns:
            The count, across every instrument set.
        """
        return len(self.moments)

    @property
    def sets(self) -> int:
        """Return how many instrument sets put ground on the feature.

        Returns:
            The count, which is the most instruments a window could hold.
        """
        return len(self.labels)


def build(coverage: Sequence[SetCoverage]) -> Track | None:
    """Merge a feature's instrument sets into one timeline the search can walk.

    An observation too small to say anything about the feature is left off the
    axis here, before anything is counted, so that the ground a set is scored
    against is the ground its admissible observations reached. Filtering later
    would score every window against ground the dataset has already decided
    does not exist.

    A set that observed the feature but filled none of its cells carries no
    ground to be found, so it is left out rather than dragging every average it
    appears in down to nothing.

    Args:
        coverage: The feature's instrument sets, in any order.

    Returns:
        The timeline, or None when no set left anything measurable behind.
    """
    sets: list[tuple[SetCoverage, Burned]] = []
    refused: list[Event] = []
    for entry in coverage:
        burned, missed = _burned(entry.events, _width(entry))
        refused.extend(missed)
        if burned:
            sets.append((entry, burned))
    if not sets:
        return None
    merged = [
        (event, filled, owner)
        for owner, (_, burned) in enumerate(sets)
        for event, filled in burned
    ]
    merged.sort(key=lambda item: item[0].t_start)  # one axis, oldest first
    return Track(
        moments=[event.t_start for event, _, _ in merged],
        times=[
            event.t_start.timestamp() / configs.DAY_SECONDS for event, _, _ in merged
        ],
        owners=[owner for _, _, owner in merged],
        cells=[filled for _, filled, _ in merged],
        grounds=[event.own_km2 for event, _, _ in merged],
        pixels=[event.pixels for event, _, _ in merged],
        sounder=[bool(event.width_km) for event, _, _ in merged],
        totals=[_total(burned) for _, burned in sets],
        labels=[entry.label for entry, _ in sets],
        grid=_grid(coverage, sets),
        refused=sorted(event.t_start for event in refused),
        sounded=_sounders(refused),
    )


def _width(entry: SetCoverage) -> float:
    """Return how wide the feature is, which a sounder track is measured against.

    Args:
        entry: One instrument set, which carries the feature's area.

    Returns:
        The side of a square of that area, in kilometres.
    """
    return math.sqrt(max(entry.summary.feature_area_km2, 0.0))


def _burned(events: Sequence[Event], width_km: float) -> tuple[Burned, list[Event]]:
    """Unpack each observation's cells once and sort the looks from the grazes.

    Args:
        events: One set's observations.
        width_km: How wide the feature is.

    Returns:
        Every observation that is a look at the feature, beside the cells it
        fills, and then the ones that said too little to be counted.
    """
    kept: Burned = []
    refused: list[Event] = []
    for event in events:
        cells = packing.cells_of(event.mask).tolist()
        if filtering.admissible(event, cells, width_km):
            kept.append((event, cells))
        else:
            refused.append(event)
    return kept, refused


def _sounders(events: Sequence[Event]) -> int:
    """Count the sounder tracks among a run of observations.

    Args:
        events: The observations to look through.

    Returns:
        How many of them were widened from a bare line, which is the only way
        an observation carries a swath width.
    """
    return sum(bool(event.width_km) for event in events)


def _total(burned: Burned) -> int:
    """Count the cells one set fills across its whole record.

    Args:
        burned: The set's observations, beside the cells each fills.

    Returns:
        The size of the union, counting a cell seen many times once.
    """
    return len({cell for _, filled in burned for cell in filled})


def _grid(
    coverage: Sequence[SetCoverage], sets: Sequence[tuple[SetCoverage, Burned]]
) -> int:
    """Size the cell array every instrument's coverage is counted in.

    The feature's cell count is how many cells fall inside it, which on a
    feature whose outline curves is fewer than the grid it was cut from, so the
    highest cell actually filled has the last word.

    Args:
        coverage: The feature's instrument sets, which agree on the grid.
        sets: The sets kept, with the cells each of their observations fills.

    Returns:
        The number of cells to make room for.
    """
    reached = max(max(filled) for _, burned in sets for _, filled in burned)
    return max(coverage[0].summary.mask_cells, reached + 1)

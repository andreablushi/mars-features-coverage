"""Every instrument's observations of one feature, merged onto one time axis."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from campaign import configs
from models.results import Event, SetCoverage
from utils import mask as packing

Filter = Callable[[Sequence[Event]], list[Event]]
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
        sounder: Whether each observation is a sounder track, one of which a
            campaign is required to hold.
        totals: How many cells each set fills across the whole record, which is
            what its reach inside a window is a share of.
        labels: The name of each set, in the order owners index them.
        grid: How many cells the feature's grid holds.
    """

    moments: list[datetime]
    times: list[float]
    owners: list[int]
    cells: list[list[int]]
    sounder: list[bool]
    totals: list[int]
    labels: list[str]
    grid: int

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


def build(
    coverage: Sequence[SetCoverage], visible: Filter | None = None
) -> Track | None:
    """Merge a feature's instrument sets into one timeline the search can walk.

    A set that observed the feature but filled none of its cells carries no
    ground to be found, so it is left out rather than dragging every average it
    appears in down to nothing.

    Args:
        coverage: The feature's instrument sets, in any order.
        visible: A filter narrowing each set to the observations to consider,
            or None to take the whole record.

    Returns:
        The timeline, or None when no set left anything measurable behind.
    """
    keep = visible or list
    sets = [(entry, _burned(keep(entry.events))) for entry in coverage]
    sets = [(entry, burned) for entry, burned in sets if burned]
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
        sounder=[bool(event.width_km) for event, _, _ in merged],
        totals=[_total(burned) for _, burned in sets],
        labels=[entry.label for entry, _ in sets],
        grid=_grid(coverage, sets),
    )


def _burned(events: Sequence[Event]) -> Burned:
    """Unpack each observation's cells once, keeping those that filled any.

    Args:
        events: One set's observations.

    Returns:
        Every observation carrying ground, beside the cells it fills.
    """
    filled = ((event, packing.cells_of(event.mask).tolist()) for event in events)
    return [(event, cells) for event, cells in filled if cells]


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

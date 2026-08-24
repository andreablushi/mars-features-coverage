"""One instrument set's observations of the ground on show, ready to draw."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from models.results import SetCoverage
from survey.models.track import Track


@dataclass(frozen=True, slots=True)
class Series:
    """What one instrument set observed of the ground on show.

    Attributes:
        label: The set's short readable name.
        times: When each of its observations started, oldest first.
        shares: How much of the ground each of them covered on its own, as a
            share of it.
        running: How much of the ground it had reached by then, as a share of
            it, counting a revisit once.
        covered: The share it ends on.
        first: The earliest moment it is drawn from, which is where a set that
            observed nothing still starts.
        last: The latest moment it is drawn to.
        reason: Why it holds nothing to draw, and empty when it observed.
    """

    label: str
    times: list[datetime]
    shares: list[float]
    running: list[float]
    covered: float
    first: datetime
    last: datetime
    reason: str

    @property
    def observed(self) -> bool:
        """Report whether the set holds any observation of the ground on show.

        Returns:
            True when it holds at least one.
        """
        return bool(self.times)


def over_feature(coverage: Sequence[SetCoverage]) -> list[Series]:
    """Read every instrument set's observations of the whole feature.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.

    Returns:
        One series per set, in the same order.
    """
    area_km2 = coverage[0].summary.feature_area_km2
    first = min(instrument.summary.t_first for instrument in coverage)
    last = max(instrument.summary.t_last for instrument in coverage)
    return [
        Series(
            label=instrument.label,
            times=[observation.t_start for observation in instrument.events],
            shares=[
                observation.own_km2 / area_km2 for observation in instrument.events
            ],
            running=[observation.cum_frac for observation in instrument.events],
            covered=instrument.summary.covered_frac,
            first=first,
            last=last,
            reason=instrument.reason,
        )
        for instrument in coverage
    ]


def over_tile(track: Track) -> list[Series]:
    """Read every instrument set's observations of one tile of a feature.

    Only the observations the search may pick from are read, so a look too
    small for the tile is left off here as it is left off the search.

    Args:
        track: The tile's admissible observations on one time axis.

    Returns:
        One series per set of the feature, in the order the track indexes
        them, holding nothing for a set that left the tile nothing.
    """
    first, last = track.observations[0].t_start, track.observations[-1].t_start
    held: list[list[int]] = [[] for _ in track.labels]
    for index in range(len(track.observations)):
        held[track.owners[index]].append(index)
    return [
        _tile_series(track, label, held[owner], first, last)
        for owner, label in enumerate(track.labels)
    ]


def _tile_series(
    track: Track, label: str, held: list[int], first: datetime, last: datetime
) -> Series:
    """Read one instrument set's observations of one tile.

    Args:
        track: The tile's admissible observations on one time axis.
        label: The set's short readable name.
        held: Where its observations sit on that axis, oldest first.
        first: The earliest moment the tile is drawn from.
        last: The latest moment it is drawn to.

    Returns:
        The series.
    """
    reached: set[int] = set()
    running = []
    for index in held:
        reached.update(track.cells[index])
        running.append(len(reached) * track.cell_km2 / track.area_km2)
    return Series(
        label=label,
        times=[track.observations[index].t_start for index in held],
        shares=[
            len(track.cells[index]) * track.cell_km2 / track.area_km2 for index in held
        ],
        running=running,
        covered=running[-1] if running else 0.0,
        first=first,
        last=last,
        reason="" if held else "nothing on this tile",
    )

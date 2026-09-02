"""One instrument set's observations of the ground on show, ready to draw."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from analysis.coverage.results import SetCoverage


@dataclass(frozen=True, slots=True)
class Series:
    """What one instrument set observed of the ground on show.

    Attributes:
        label: The set's short readable name.
        iid: The instrument it belongs to, which is what the filter names.
        times: When each of its observations started, oldest first.
        shares: How much of the ground each of them covered on its own.
        running: How much of the ground it had reached by then, revisits counted once.
        covered: The share it ends on.
        first: The earliest moment it is drawn from.
        last: The latest moment it is drawn to.
        reason: Why it holds nothing to draw, and empty when it observed.
    """

    label: str
    iid: str
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
            iid=instrument.summary.iid,
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

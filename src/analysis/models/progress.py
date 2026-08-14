"""Summary model for a finished coverage run."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunSummary:
    """Totals for a finished run.

    Attributes:
        computed: Instrument sets that produced rows.
        empty: Instrument sets that ran but had nothing left to measure.
        failed: Instrument sets that raised an error.
        events: Observation rows written across every set.
        discarded: Stored records that carried no footprint or no start time.
        elapsed: Total run duration in seconds.
    """

    computed: int
    empty: int
    failed: int
    events: int
    discarded: int
    elapsed: float

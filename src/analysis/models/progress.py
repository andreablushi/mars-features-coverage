"""Summary model for a finished coverage run."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunSummary:
    """Totals for a finished run.

    Attributes:
        computed: Features computed successfully.
        failed: Features that raised an error.
        events: Observation rows written across every feature.
        elapsed: Total run duration in seconds.
    """

    computed: int
    failed: int
    events: int
    elapsed: float

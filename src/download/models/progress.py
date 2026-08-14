"""Summary model for a finished download run."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunSummary:
    """Totals for a finished run.

    Attributes:
        ran: Jobs executed successfully.
        failed: Jobs that raised an error.
        elapsed: Total run duration in seconds.
    """

    ran: int
    failed: int
    elapsed: float

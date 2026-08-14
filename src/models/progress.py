"""Progress reporting shared by both pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Outcome(Protocol):
    """What every runner reports back about one finished unit of work."""

    @property
    def label(self) -> str:
        """Return a short human readable name for the work.

        Returns:
            The name to show beside a failure.
        """

    @property
    def failed(self) -> bool:
        """Report whether the work raised an error.

        Returns:
            True when an error was recorded.
        """

    @property
    def error(self) -> Exception | None:
        """Return what went wrong.

        Returns:
            The error raised, or None on success.
        """


@dataclass(frozen=True)
class ProgressEvent:
    """A snapshot of run progress, emitted as each unit of work finishes.

    Attributes:
        completed: Units finished so far, successful or not.
        outcome: The unit that just finished.
    """

    completed: int
    outcome: Outcome


@dataclass(frozen=True, slots=True)
class DownloadSummary:
    """Totals for a finished download run.

    Attributes:
        ran: Jobs executed successfully.
        failed: Jobs that raised an error.
        elapsed: Total run duration in seconds.
    """

    ran: int
    failed: int
    elapsed: float


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    """Totals for a finished coverage run.

    Attributes:
        computed: Instrument sets that produced rows.
        empty: Instrument sets that ran but had nothing left to measure.
        failed: Instrument sets that raised an error.
        events: Observation rows written across every set.
        discarded: Records carrying no footprint, no start time, or no overlap.
        elapsed: Total run duration in seconds.
    """

    computed: int
    empty: int
    failed: int
    events: int
    discarded: int
    elapsed: float

"""Progress and summary models emitted by the runner."""

from __future__ import annotations

from dataclasses import dataclass

from download.models.job import JobOutcome


@dataclass(frozen=True)
class ProgressEvent:
    """A snapshot of run progress, emitted after each job finishes.

    The runner produces these and never renders them, so the caller decides
    whether they become a progress bar, a log line, or nothing at all.

    Attributes:
        completed: Jobs finished so far, successful or not.
        outcome: The job that just finished.
    """

    completed: int
    outcome: JobOutcome


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

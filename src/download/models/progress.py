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
        total: Jobs in the run.
        elapsed: Seconds since the run started.
        outcome: The job that just finished.
        rows: Product records written so far.
        failed: Jobs that raised an error so far.
    """

    completed: int
    total: int
    elapsed: float
    outcome: JobOutcome
    rows: int
    failed: int

    @property
    def fraction(self) -> float:
        """Return the completed fraction of the run.

        Returns:
            A value between 0.0 and 1.0, or 1.0 when there is no work.
        """
        return self.completed / self.total if self.total else 1.0

    @property
    def percentage(self) -> float:
        """Return the completed percentage of the run.

        Returns:
            A value between 0.0 and 100.0.
        """
        return self.fraction * 100.0

    @property
    def eta_seconds(self) -> float | None:
        """Estimate the seconds remaining from the average job duration.

        Returns:
            The estimate, or None before the first job completes.
        """
        if self.completed == 0:
            return None
        return (self.elapsed / self.completed) * (self.total - self.completed)


@dataclass(frozen=True)
class RunSummary:
    """Totals for a finished run.

    Attributes:
        ran: Jobs executed successfully.
        rows: Total product records written.
        empty: Jobs that matched no products.
        failed: Jobs that raised an error.
        elapsed: Total run duration in seconds.
    """

    ran: int
    rows: int
    empty: int
    failed: int
    elapsed: float

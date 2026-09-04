"""The unit of work the download stage runs, and what it reports back."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Job:
    """One product to bring down, and the archive that brings it.

    Attributes:
        instrument: The instrument that fetches it, as ODE names it.
        identifier: What that instrument is asked for, its own observation or tile.
    """

    instrument: str
    identifier: str

    @property
    def label(self) -> str:
        """Return a short human readable name for this job.

        Returns:
            What was asked for, and the instrument it was asked of.
        """
        return f"{self.identifier} [{self.instrument}]"


@dataclass(frozen=True, slots=True)
class Outcome:
    """The result of running one download job.

    Attributes:
        job: The job that was run.
        landed: Where each product it brought down sits on disk.
        error: The error raised, or None on success.
    """

    job: Job
    landed: tuple[Path, ...] = ()
    error: Exception | None = None

    @property
    def label(self) -> str:
        """Return a short human readable name for the job that was run.

        Returns:
            The label of the underlying job.
        """
        return self.job.label

    @property
    def failed(self) -> bool:
        """Return whether the job raised an error.

        Returns:
            True when an error was recorded.
        """
        return self.error is not None

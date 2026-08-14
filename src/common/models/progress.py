"""Progress reporting shared by both pipelines.

A runner produces these and never renders them, so the caller decides whether
they become a progress bar, a log line, or nothing at all.
"""

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

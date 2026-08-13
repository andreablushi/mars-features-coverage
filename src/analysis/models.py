"""Progress and summary models emitted by the coverage runner."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureOutcome:
    """What happened when one feature's coverage was computed.

    Attributes:
        label: The feature class and name, for display.
        events: How many observation rows were written.
        degenerate: Whether the feature's bounding box encloses no area.
        error: The failure, or None when the feature computed cleanly.
    """

    label: str
    events: int = 0
    degenerate: bool = False
    error: Exception | None = None

    @property
    def failed(self) -> bool:
        """Report whether the feature failed to compute.

        Returns:
            True when the feature raised an error.
        """
        return self.error is not None


@dataclass(frozen=True)
class ProgressEvent:
    """A snapshot of run progress, emitted after each feature finishes.

    The runner produces these and never renders them, so the caller decides
    whether they become a progress bar, a log line, or nothing at all.

    Attributes:
        completed: Features finished so far, successful or not.
        outcome: The feature that just finished.
    """

    completed: int
    outcome: FeatureOutcome


@dataclass(frozen=True)
class RunSummary:
    """Totals for a finished run.

    Attributes:
        features: Features computed successfully.
        failed: Features that raised an error.
        degenerate: Features skipped for having a zero-area bounding box.
        events: Observation rows written across every feature.
        elapsed: Total run duration in seconds.
    """

    features: int
    failed: int
    degenerate: int
    events: int
    elapsed: float

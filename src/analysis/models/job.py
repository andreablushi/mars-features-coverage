"""Coverage job models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoverageJob:
    """One feature to compute coverage for.

    Attributes:
        source: The metadata directory holding one JSONL file per set.
        events_path: The parquet file the per-observation rows go to.
        summary_path: The parquet file the per-instrument-set rows go to.
    """

    source: Path
    events_path: Path
    summary_path: Path

    @property
    def label(self) -> str:
        """Return a short human readable name for this job.

        Returns:
            The feature class and name slugs, joined by a slash.
        """
        return f"{self.source.parent.name}/{self.source.name}"


@dataclass(frozen=True)
class JobOutcome:
    """The result of running a single job.

    Attributes:
        job: The job that was run.
        events: How many observation rows were written.
        error: The error raised, or None on success.
    """

    job: CoverageJob
    events: int = 0
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


@dataclass(frozen=True)
class CoveragePlan:
    """The work selected for a run.

    Attributes:
        jobs: Features that still need computing.
        feature_count: Features discovered on disk.
        skipped_existing: Features left alone because they are already done.
    """

    jobs: tuple[CoverageJob, ...]
    feature_count: int
    skipped_existing: int

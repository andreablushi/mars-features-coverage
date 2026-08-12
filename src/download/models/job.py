"""Download job models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from download.models.feature import Feature
from download.models.instrument import InstrumentSet


@dataclass(frozen=True)
class Job:
    """One feature and instrument set to download.

    Attributes:
        feature: The feature to query.
        instrument_set: The instrument set to query.
        output_path: The JSONL file the results are written to.
    """

    feature: Feature
    instrument_set: InstrumentSet
    output_path: Path

    @property
    def label(self) -> str:
        """Return a short human readable name for this job.

        Returns:
            The feature name followed by the instrument set key.
        """
        return f"{self.feature.name} [{self.instrument_set.key}]"


@dataclass(frozen=True)
class JobOutcome:
    """The result of running a single job.

    Attributes:
        job: The job that was run.
        rows: Product records written, or 0 when the job failed.
        error: The error raised, or None on success.
    """

    job: Job
    rows: int
    error: Exception | None = None

    @property
    def failed(self) -> bool:
        """Return whether the job raised an error.

        Returns:
            True when an error was recorded.
        """
        return self.error is not None


@dataclass(frozen=True)
class DownloadPlan:
    """The work selected for a run.

    Attributes:
        jobs: Jobs that still need downloading.
        feature_count: Usable features selected.
        instrument_set_count: Instrument sets selected.
        degenerate_features: Features skipped for having a zero area box.
        skipped_existing: Outputs left in place because they already exist.
    """

    jobs: tuple[Job, ...]
    feature_count: int
    instrument_set_count: int
    degenerate_features: int
    skipped_existing: int

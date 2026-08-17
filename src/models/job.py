"""The unit of work each stage runs, and what it reports back."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from models.feature import Feature
from models.instrument import InstrumentSet

Job = TypeVar("Job")


@dataclass(frozen=True, slots=True)
class DownloadJob:
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


@dataclass(frozen=True, slots=True)
class CoverageJob:
    """One feature and instrument set to compute coverage for.

    Splitting the work per instrument set rather than per feature keeps the
    pool busy, since a feature's sets differ in size by orders of magnitude.

    Attributes:
        source: The JSONL file holding one instrument set's observations.
        events_path: The parquet file the per-observation rows go to.
        summary_path: The parquet file the set's one summary row goes to,
            written last so its presence marks the set as finished.
        geometry_path: The parquet file caching the projected footprints.
    """

    source: Path
    events_path: Path
    summary_path: Path
    geometry_path: Path

    @property
    def label(self) -> str:
        """Return a short human readable name for this job.

        Returns:
            The feature slug followed by the instrument set slug.
        """
        return f"{self.source.parent.name}/{self.source.stem}"


@dataclass(frozen=True, slots=True)
class DownloadOutcome:
    """The result of running one download job.

    Attributes:
        job: The job that was run.
        error: The error raised, or None on success.
    """

    job: DownloadJob
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


@dataclass(frozen=True, slots=True)
class CoverageOutcome:
    """The result of running one coverage job.

    Attributes:
        job: The job that was run.
        events: How many observation rows were written.
        discarded: How many stored records could not be measured.
        error: The error raised, or None on success.
    """

    job: CoverageJob
    events: int = 0
    discarded: int = 0
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

    @property
    def empty(self) -> bool:
        """Return whether the job finished having measured nothing.

        Returns:
            True when the set produced no observation rows.
        """
        return self.error is None and self.events == 0


@dataclass(frozen=True, slots=True)
class DownloadPlan:
    """The download work selected for a run.

    Attributes:
        jobs: Jobs that still need downloading.
        feature_count: Usable features selected.
        instrument_set_count: Instrument sets selected.
        sizeless_features: Names of the features the catalogue gives no extent
            that could be recovered, which were left unqueried.
        skipped_existing: Outputs left in place because they already exist.
    """

    jobs: tuple[DownloadJob, ...]
    feature_count: int
    instrument_set_count: int
    sizeless_features: tuple[str, ...]
    skipped_existing: int


@dataclass(frozen=True, slots=True)
class CoveragePlan:
    """The coverage work selected for a run.

    Attributes:
        jobs: Instrument sets that still need computing.
        feature_count: Features discovered on disk.
        set_count: Instrument sets discovered on disk.
        skipped_existing: Sets left alone because they are already computed.
    """

    jobs: tuple[CoverageJob, ...]
    feature_count: int
    set_count: int
    skipped_existing: int

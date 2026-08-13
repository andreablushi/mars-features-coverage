"""Coverage job models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoverageJob:
    """One feature and instrument set to compute coverage for.

    Splitting the work per instrument set rather than per feature keeps the
    pool busy. A feature's sets differ in size by orders of magnitude, so one
    job per feature leaves a single worker grinding through the largest set
    while the rest idle.

    Attributes:
        source: The JSONL file holding one instrument set's observations.
        events_path: The parquet file the per-observation rows go to.
        geometry_path: The parquet file caching the projected footprints.
    """

    source: Path
    events_path: Path
    geometry_path: Path

    @property
    def summary_path(self) -> Path:
        """Return where this set's own summary row belongs.

        Returns:
            The path to the summary parquet file beside the events.
        """
        stem = self.events_path.name[: -len(".events.parquet")]
        return self.events_path.with_name(stem + ".summary.parquet")

    @property
    def label(self) -> str:
        """Return a short human readable name for this job.

        Returns:
            The feature slug followed by the instrument set slug.
        """
        return f"{self.source.parent.name}/{self.source.stem}"


@dataclass(frozen=True)
class JobOutcome:
    """The result of running a single job.

    Attributes:
        job: The job that was run.
        events: How many observation rows were written.
        discarded: How many stored records carried no footprint or no start
            time and so could not be measured.
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
        """Return whether the job ran but had nothing left to measure.

        Returns:
            True when no error was raised and no row was written.
        """
        return self.error is None and self.events == 0


@dataclass(frozen=True)
class CoveragePlan:
    """The work selected for a run.

    Attributes:
        jobs: Instrument sets that still need computing.
        feature_count: Features discovered on disk.
        set_count: Instrument sets discovered across them.
        skipped_existing: Sets left alone because they are already done.
    """

    jobs: tuple[CoverageJob, ...]
    feature_count: int
    set_count: int
    skipped_existing: int

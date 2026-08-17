"""The unit of work each stage runs, and what it reports back."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.feature import Feature
from models.instrument import InstrumentSet


@dataclass(frozen=True, slots=True)
class Job:
    """One feature and instrument set to download, or to compute coverage for.

    A download job carries what to query and where to put it; a coverage job
    carries the metadata file to read and the artifacts to write beside it.

    Attributes:
        feature: The feature to query, on a download job.
        instrument_set: The instrument set to query, on a download job.
        output_path: The JSONL file the results are written to.
        source: The JSONL file holding one instrument set's observations.
        events_path: The parquet file the per-observation rows go to.
        summary_path: The parquet file the set's one summary row goes to,
            written last so its presence marks the set as finished.
        geometry_path: The parquet file caching the projected footprints.
    """

    feature: Feature | None = None
    instrument_set: InstrumentSet | None = None
    output_path: Path | None = None
    source: Path | None = None
    events_path: Path | None = None
    summary_path: Path | None = None
    geometry_path: Path | None = None

    @property
    def label(self) -> str:
        """Return a short human readable name for this job.

        Returns:
            The feature name and instrument set key on a download job, the
            feature slug and instrument set slug on a coverage job.
        """
        if self.feature is not None and self.instrument_set is not None:
            return f"{self.feature.name} [{self.instrument_set.key}]"
        return f"{self.source.parent.name}/{self.source.stem}"


@dataclass(frozen=True, slots=True)
class Outcome:
    """The result of running one job.

    Attributes:
        job: The job that was run.
        events: How many observation rows were written.
        discarded: How many stored records could not be measured.
        error: The error raised, or None on success.
    """

    job: Job
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
class Plan:
    """The work selected for one half of a run.

    Attributes:
        jobs: The jobs that still need running.
        feature_count: Features selected, or discovered on disk.
        set_count: Instrument sets selected, or discovered on disk.
        skipped_existing: Outputs left in place because they already exist.
        sizeless_features: Names of the features the catalogue gives no extent
            that could be recovered, which were left unqueried.
    """

    jobs: tuple[Job, ...]
    feature_count: int
    set_count: int
    skipped_existing: int
    sizeless_features: tuple[str, ...] = ()

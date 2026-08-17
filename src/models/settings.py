"""What one run was asked to do, once every source has been read."""

from __future__ import annotations

from dataclasses import dataclass

from models.instrument import InstrumentSet


@dataclass(frozen=True, slots=True)
class DownloadSettings:
    """The settled choices for the download stage.

    Attributes:
        instrument_sets: The instrument sets to download for every feature.
        feature_names: The features to restrict the run to, or None for the
            whole catalogue.
        loc: Which products ODE returns for a feature box, "f" for every
            footprint that overlaps it and "o" for only those fully inside.
    """

    instrument_sets: tuple[InstrumentSet, ...]
    feature_names: tuple[str, ...] | None
    loc: str


@dataclass(frozen=True, slots=True)
class PipelineSettings:
    """The settled choices for the run as a whole.

    Attributes:
        keep_metadata: Whether to keep a set's downloaded JSONL once its
            coverage is computed. Deleting it makes the artifacts final, since
            nothing can be recomputed without downloading again.
        force: Whether to redo finished work rather than skip it, which covers
            both halves at once: a set is downloaded again and measured again.
        refresh_catalog: Whether to re-fetch the ODE catalogues rather than
            reading the cached copies.
        workers: How many jobs each half runs at once, downloads on threads and
            coverage on processes.
    """

    keep_metadata: bool
    force: bool
    refresh_catalog: bool
    workers: int

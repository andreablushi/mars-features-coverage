"""What one run was asked to do, once every source has been read."""

from __future__ import annotations

from dataclasses import dataclass

from models.instrument import InstrumentSet


@dataclass(frozen=True, slots=True)
class DownloadSettings:
    """The settled choices for the download stage.

    Attributes:
        instrument_sets: The instrument sets to download for every feature.
        loc: Which products ODE returns for a feature box, "f" for every
            footprint that overlaps it and "o" for only those fully inside.
        point_radius_deg: Half the width of the box put around a feature the
            catalogue records by centre alone, in degrees of latitude.
        force: Whether to re-download instead of skipping finished files.
        workers: How many downloads to run at once.
    """

    instrument_sets: tuple[InstrumentSet, ...]
    loc: str
    point_radius_deg: float
    force: bool
    workers: int


@dataclass(frozen=True, slots=True)
class CoverageSettings:
    """The settled choices for the coverage stage.

    Attributes:
        cumulative_union: Whether to accumulate the running union of covered
            ground, which is the whole of what the union costs. Off leaves each
            observation's own area measured and the union columns empty.
        force: Whether to recompute instead of skipping finished sets.
        workers: How many sets to compute at once.
    """

    cumulative_union: bool
    force: bool
    workers: int


@dataclass(frozen=True, slots=True)
class PipelineSettings:
    """The settled choices for the run as a whole.

    Attributes:
        keep_metadata: Whether to keep a set's downloaded JSONL once its
            coverage is computed. Deleting it makes the artifacts final, since
            nothing can be recomputed without downloading again.
        coverage_only: Whether to skip downloading and only measure what is
            already on disk.
    """

    keep_metadata: bool
    coverage_only: bool

"""What one download run was asked to do, once every source has been read."""

from __future__ import annotations

from dataclasses import dataclass

from download.models.instrument import InstrumentSet


@dataclass(frozen=True, slots=True)
class DownloadSettings:
    """The settled choices for a run, whatever they were asked for through.

    Attributes:
        instrument_sets: The instrument sets to download for every feature.
        loc: Which products ODE returns for a feature box, "f" for every
            footprint that overlaps it and "o" for only those fully inside.
        force: Whether to re-download instead of skipping finished files.
        workers: How many downloads to run at once.
    """

    instrument_sets: tuple[InstrumentSet, ...]
    loc: str
    force: bool
    workers: int

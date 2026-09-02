"""What one run was asked to do, once every source has been read."""

from __future__ import annotations

from dataclasses import dataclass

from analysis.models.instrument import InstrumentSet


@dataclass(frozen=True, slots=True)
class Settings:
    """The settled choices for a run, read from one flat config file.

    Attributes:
        grid_cells: Cells along each axis of one block.
        instrument_sets: The instrument sets to download for every feature.
        plot_instrument_sets: The sets the figures draw, or None for every one held.
        loc: "f" for every footprint overlapping the box, "o" for only those inside.
        keep_metadata: Whether to keep a set's JSONL once its coverage is computed.
        force: Whether to redo finished work rather than skip it, which covers
        both halves at once: a set is downloaded again and measured again.
        refresh_catalog: Whether to re-fetch the ODE catalogues, not read the cache.
        workers: How many jobs each half runs at once.
    """

    grid_cells: int
    instrument_sets: tuple[InstrumentSet, ...]
    plot_instrument_sets: tuple[InstrumentSet, ...] | None
    loc: str
    keep_metadata: bool
    force: bool
    refresh_catalog: bool
    workers: int

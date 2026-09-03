"""Computing one instrument set's coverage of its feature, start to finish."""

from __future__ import annotations

from analysis.coverage.artifacts import writing
from analysis.coverage.measuring import measuring
from analysis.coverage.projection import projecting
from analysis.models.job import Job
from analysis.models.observation import ObservationSet


def compute(job: Job, loaded: ObservationSet, grid_cells: int) -> tuple[int, int]:
    """Measure one instrument set's coverage of its feature and write it out.

    Args:
        job: The instrument set being computed, naming both destinations.
        loaded: The set's stored observations, in chronological order.
        grid_cells: How many cells one block of the feature's grid holds per axis.

    Returns:
        How many observation rows were written, and how many records were discarded.
    """
    projected = projecting.project(loaded)
    if not projected.observations:
        return 0, projected.discarded
    events, summary = measuring.measure_set(projected, grid_cells)
    writing.write_coverage(job, events, summary)
    return len(events), projected.discarded

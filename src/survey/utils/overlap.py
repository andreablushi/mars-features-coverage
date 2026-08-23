"""How much of a feature more than one instrument set reaches inside a window."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.survey import Survey
from survey.models.track import Track


def reached(track: Track, picked: Survey) -> list[int]:
    """Count how many instrument sets reach each cell of the feature.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window they are counted inside.

    Returns:
        How many sets reach each cell of the feature's grid, cell by cell.
    """
    held: list[set[int]] = [set() for _ in track.totals]
    for owner, observation, filled in zip(
        track.owners, track.observations, track.cells, strict=True
    ):
        if picked.start <= observation.t_start <= picked.end:
            held[owner].update(filled)
    counted = [0] * track.grid
    for filled in held:
        for cell in filled:
            counted[cell] += 1
    return counted


def share(counted: Sequence[int], wanted: int, cells: int) -> float:
    """Work out how much of the feature that many instrument sets all reach.

    Args:
        counted: How many sets reach each cell of the feature's grid.
        wanted: The least number of sets a cell has to be reached by to count,
            so asking for two counts the ground three reach as well.
        cells: How many cells of the feature's grid fall inside it, which is
            what the count is a share of.

    Returns:
        The share of the feature, between zero and one, or nought when the
        feature was never gridded.
    """
    if not cells:
        return 0.0
    return sum(1 for sets in counted if sets >= wanted) / cells

"""How much of a feature more than one instrument set reaches inside a window."""

from __future__ import annotations

from collections.abc import Sequence

from survey.models.survey import Survey
from survey.models.track import Track


def reached(track: Track, picked: Survey) -> list[int]:
    """Count how many instrument sets reach each cell of the tile.

    Args:
        track: The tile's admissible observations on one time axis.
        picked: The window they are counted inside.

    Returns:
        How many sets reach each cell of the tile's grid, cell by cell.
    """
    held: list[set[int]] = [set() for _ in track.labels]
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


def ground(counted: Sequence[int], wanted: int, cell_km2: float) -> float:
    """Work out how much ground that many instrument sets all reach.

    Args:
        counted: How many sets reach each cell of the tile's grid.
        wanted: The least number of sets a cell has to be reached by to count,
            so asking for two counts the ground three reach as well.
        cell_km2: How much ground one cell of that grid covers.

    Returns:
        The ground in square kilometres.
    """
    return sum(1 for sets in counted if sets >= wanted) * cell_km2

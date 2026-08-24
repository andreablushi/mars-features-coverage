"""Which instruments reach the ground a window holds, and how much of it."""

from __future__ import annotations

from survey.models.survey import Survey
from survey.models.track import Track


def reached(track: Track, picked: Survey) -> dict[tuple[str, ...], float]:
    """Work out how much ground each set of instruments reaches between them.

    Args:
        track: The tile's admissible observations on one time axis.
        picked: The window they are counted inside.

    Returns:
        The ground in square kilometres, by the instruments that reach it,
        named in order. A cell counts once, under the instruments that are
        really there, so the grounds do not overlap and add up to what the
        window covers.
    """
    filled: list[set[int]] = [set() for _ in track.labels]
    for index in picked.kept:
        filled[track.owners[index]].update(track.cells[index])
    here: list[set[str]] = [set() for _ in range(track.grid)]
    for owner, cells in enumerate(filled):
        for cell in cells:
            here[cell].add(track.iids[owner])
    found: dict[tuple[str, ...], float] = {}
    for instruments in here:
        if instruments:
            names = tuple(sorted(instruments))
            found[names] = found.get(names, 0.0) + track.cell_km2
    return found

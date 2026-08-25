"""What the whole record answers for, when a window cannot be asked for it."""

from __future__ import annotations

from collections.abc import Container

from survey.models.track import Track


def kept(track: Track, instruments: Container[str]) -> tuple[int, ...]:
    """Keep every look a timeless instrument left on the tile, whenever it came.

    A timeless instrument is gathered whether or not a demand names it. What a
    sounder reads is the rock under the ground, which is worth having on the
    tile even where the tile was chosen for what the imagers saw, so asking for
    it is one thing and taking it is another.

    Args:
        track: The tile's admissible observations on one time axis.
        instruments: The instruments the ground answers for whenever they came.

    Returns:
        Where those observations sit on the axis, oldest first, keeping only
        the ones bringing ground their own instrument does not already hold,
        and nothing at all when the strategy names no timeless instrument.
    """
    answering = {owner for owner, iid in enumerate(track.iids) if iid in instruments}
    reached: dict[int, set[int]] = {}
    held: list[int] = []
    for index, owner in enumerate(track.owners):
        if owner not in answering:
            continue
        seen = reached.setdefault(owner, set())
        if not set(track.cells[index]) <= seen:
            seen.update(track.cells[index])
            held.append(index)
    return tuple(held)

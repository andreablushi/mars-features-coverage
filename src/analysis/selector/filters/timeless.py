"""What the whole record answers for, when a window cannot be asked for it."""

from __future__ import annotations

from collections.abc import Container

from analysis.selector.models.track import Track


def fresh_looks(track: Track, instruments: Container[str]) -> tuple[int, ...]:
    """Keep every look a timeless instrument left on the feature, whenever it came.

    Args:
        track: The feature's admissible observations on one time axis.
        instruments: The instruments the ground answers for whenever they came.

    Returns:
        Where they sit on the axis, oldest first, keeping only what brings new ground.
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

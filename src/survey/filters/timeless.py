"""What the whole record answers for, when a window cannot be asked for it."""

from __future__ import annotations

from survey.models.strategy import Demands
from survey.models.track import Track


def kept(track: Track, standing: Demands) -> tuple[int, ...]:
    """Keep the observations answering what time cannot change.

    Args:
        track: The tile's admissible observations on one time axis.
        standing: The cells each timeless instrument has to reach, whenever it
            reached them.

    Returns:
        Where those observations sit on the axis, oldest first, and nothing at
        all when the strategy asks nothing of the whole record.
    """
    answering = {
        owner for answers in standing for owners, _ in answers for owner in owners
    }
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

"""Which observations inside a window brought ground the window did not hold."""

from __future__ import annotations

from survey import configs
from survey.models.track import Track
from survey.models.window import Window


def trimming(track: Track, window: Window) -> int:
    """Separate the observations that add coverage from the ones that repeat it.

    Args:
        track: The feature's observations on one time axis.
        window: The window they are counted inside.

    Returns:
        How many of its observations brought ground of their own.
    """
    seen: dict[int, set[int]] = {}
    counted = 0
    for index in range(window.first, window.last + 1):
        # Each set is scored against its own record, so each keeps its own seen cells.
        held = seen.setdefault(track.owners[index], set())
        # Ground its own set had not reached anywhere earlier in the window
        fresh = [cell for cell in track.cells[index] if cell not in held]
        if len(fresh) * track.cell_km2 >= configs.MIN_GAIN_KM2:
            counted += 1
        # A cell is held once however many observations go on to fill it
        held.update(fresh)
    return counted

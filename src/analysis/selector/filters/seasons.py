"""Cutting one feature's timeline into the Mars seasons its observations fall in."""

from __future__ import annotations

from analysis.selector.models.track import Track
from analysis.selector.models.window import Window


def cut(track: Track) -> list[Window]:
    """Cut a timeline into one window for each Mars season it reaches into.

    Args:
        track: The admissible observations on one time axis, oldest first.

    Returns:
        One window per season holding any observation, oldest first. A season
        runs on unbroken, so each of them is one stretch of the axis.
    """
    held = track.seasons
    windows: list[Window] = []
    first = 0
    for index in range(1, len(held) + 1):
        if index < len(held) and held[index] == held[first]:
            continue
        last = index - 1
        windows.append(Window(first, last, track.times[last] - track.times[first]))
        first = index
    return windows

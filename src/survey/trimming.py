"""Which observations inside a window brought ground the window did not hold."""

from __future__ import annotations

from survey import configs
from survey.results import Span
from survey.timeline import Track


def core(track: Track, span: Span) -> int:
    """Count the observations a window would still reach the same ground without.

    A window covers a cell once however many observations fill it, so a set
    that images the same ground twice adds the second look for nothing. Each
    observation is asked what it brought that nothing before it in the window
    had already brought from its own set, which is the share its set is scored
    on. The ones that brought too little are redundant: dropping them leaves
    the window covering the same ground over the same days.

    Walking the window oldest first rather than reordering it by what each
    observation adds picks a different set of redundant observations than the
    greedy order would, and the same union either way, at a cost a feature
    holding tens of thousands of observations can afford.

    Args:
        track: The feature's observations on one time axis.
        span: The window they are counted inside.

    Returns:
        How many of its observations brought ground of their own.
    """
    seen: dict[int, set[int]] = {}
    counted = 0
    for index in range(span.first, span.last + 1):
        held = seen.setdefault(track.owners[index], set())
        fresh = [cell for cell in track.cells[index] if cell not in held]
        if len(fresh) >= configs.MIN_GAIN_CELLS:
            counted += 1
        held.update(fresh)
    return counted

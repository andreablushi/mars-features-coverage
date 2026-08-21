"""What a window that the sweep settled on turns out to hold."""

from __future__ import annotations

from survey.models.track import Track
from survey.reach import Reach
from survey.results import Span


def widen(track: Track, span: Span, wanted: int = 0) -> Span:
    """Take in every observation sharing an instant with either end.

    A window is a stretch of time, so anything taken at the very moment it
    opens or closes belongs inside it. Two observations timed to the same
    second are common, and leaving one of them out would drop its ground while
    costing not a second less.

    Args:
        track: The feature's observations on one time axis.
        span: The window the sweep settled on.
        wanted: How many instrument sets the search is insisting on, which is
            how many its score is taken over. Nought for all of them.

    Returns:
        The same stretch of time, holding everything taken during it.
    """
    first, last = span.first, span.last
    while first and track.times[first - 1] == track.times[first]:
        first -= 1
    while (
        last + 1 < len(track.observations)
        and track.times[last + 1] == track.times[last]
    ):
        last += 1
    if (first, last) == (span.first, span.last):
        return span
    held = measure(track, first, last, wanted)
    return Span(first, last, span.days, held.mean, held.instruments)


def measure(track: Track, first: int, last: int, wanted: int = 0) -> Reach:
    """Fill a fresh tally with everything one window holds.

    Args:
        track: The feature's observations on one time axis.
        first: The index of the earliest observation it holds.
        last: The index of the latest one.
        wanted: How many instrument sets the score is taken over. Nought for
            all of them.

    Returns:
        The tally, holding that window and nothing else.
    """
    held = Reach(track.totals, track.grid, wanted)
    for index in range(first, last + 1):
        held.hold(track.owners[index], track.cells[index])
    return held


def shares(track: Track, span: Span) -> dict[str, float]:
    """Work out what each instrument set reaches inside one window.

    Args:
        track: The feature's observations on one time axis.
        span: The window to break down.

    Returns:
        The share of its own ground each set reaches, by set name.
    """
    held = measure(track, span.first, span.last)
    return dict(zip(track.labels, held.shares, strict=True))

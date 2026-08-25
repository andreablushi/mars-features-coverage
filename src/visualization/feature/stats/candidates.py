"""Every window one tile's record could be clustered into, and what each holds."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from matplotlib.dates import date2num

from survey.models.counter import Counter
from survey.models.strategy import Strategy
from survey.models.track import Track

# The grid of candidate windows one tile's record is scored on.
WINDOW_COLUMNS = 240
WINDOW_WIDTHS = 64
WINDOW_MIN_DAYS = 1.0


@dataclass(frozen=True, slots=True)
class Grid:
    """What every candidate window over one tile holds.

    Attributes:
        centres: The moment each column's window is centred on, as date
            numbers. A window reaches half its length either side of it.
        widths: How long each row's window lasts, in days, up to the longest
            the strategy lets a window run.
        reached: The share of the tile a window covers, counted evenly over
            the instrument sets that left anything on it, one value per width
            and centre.
        instruments: How many instruments observed the tile inside every
            window, shaped as reached.
        sounded: Whether every window holds a sounder track, shaped as
            reached.
    """

    centres: np.ndarray
    widths: np.ndarray
    reached: np.ndarray
    instruments: np.ndarray
    sounded: np.ndarray


def build(track: Track, strategy: Strategy) -> Grid | None:
    """Score every window the tile's observations could be clustered into.

    A sounder publishes a bare line, so a swath width is the only mark an
    observation carries of having been widened from one, and a running total
    of those turns the count inside a stretch into a difference across it.

    Args:
        track: The tile's admissible observations on one time axis.
        strategy: What a window over it is asked for, which caps how long a
            window on the panel may run.

    Returns:
        The scored grid, or None when the record is too short to hold a choice
        of windows at all.
    """
    if not track.area_km2:
        return None
    moments = date2num([observation.t_start for observation in track.observations])
    span = float(moments[-1] - moments[0])
    if span < WINDOW_MIN_DAYS:
        return None
    centres = np.linspace(moments[0], moments[-1], WINDOW_COLUMNS)
    widths = np.geomspace(WINDOW_MIN_DAYS, min(span, strategy.span_days), WINDOW_WIDTHS)
    observed = sorted(set(track.owners))
    widened = [1 if one.width_km else 0 for one in track.observations]
    flown = np.concatenate([[0], np.cumsum(widened)])
    rows = [_row(track, moments, centres, width, observed, flown) for width in widths]
    return Grid(
        centres=centres,
        widths=widths,
        reached=np.array([reached for reached, _, _ in rows]),
        instruments=np.array([counted for _, counted, _ in rows]),
        sounded=np.array([sounded for _, _, sounded in rows]),
    )


def _row(
    track: Track,
    moments: np.ndarray,
    centres: np.ndarray,
    width: float,
    observed: list[int],
    flown: np.ndarray,
) -> tuple[list[float], list[int], list[bool]]:
    """Score every window of one length, sliding it along the time axis.

    The windows of one length are scored in order, so the counter behind them
    is slid from one to the next rather than rebuilt for each.

    Args:
        track: The tile's admissible observations on one time axis.
        moments: When each of them started, as date numbers, in order.
        centres: The moment each window is centred on, earliest first.
        width: How long the windows last, in days.
        observed: The instrument sets that left anything on the tile.
        flown: The running total of sounder tracks along the axis.

    Returns:
        What each window covers, how many instruments observed inside it, and
        whether a sounder flew through it, in the order the centres come.
    """
    counter = Counter.empty(track.iids, track.grid)
    first = np.searchsorted(moments, centres - width / 2.0, side="left")
    last = np.searchsorted(moments, centres + width / 2.0, side="right")
    share = track.cell_km2 / track.area_km2
    reached: list[float] = []
    instruments: list[int] = []
    sounded: list[bool] = []
    low = high = 0
    for opens, closes in zip(first, last, strict=True):
        while high < closes:
            counter.hold(track.owners[high], track.cells[high])
            high += 1
        while low < opens:
            counter.release(track.owners[low], track.cells[low])
            low += 1
        filled = [counter.cells_reached[owner] for owner in observed]
        reached.append(_evenly(filled) * share)
        instruments.append(
            len(
                {
                    track.iids[owner]
                    for owner in observed
                    if counter.cells_reached[owner]
                }
            )
        )
        sounded.append(bool(flown[closes] - flown[opens]))
    return reached, instruments, sounded


def _evenly(filled: list[int]) -> float:
    """Count what the instrument sets cover the way the search counts it.

    Args:
        filled: How many cells of the tile each set that observed it reaches
            inside the window.

    Returns:
        The counts multiplied and rooted, so that a window one set misses
        reads as the poor window the search takes it for.
    """
    product = 1.0
    for count in filled:
        product *= count
    return product ** (1.0 / len(filled))

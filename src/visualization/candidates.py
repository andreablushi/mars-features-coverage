"""Every window a feature's record could be clustered into, and what each holds."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from matplotlib.dates import date2num

from models.results import Event, SetCoverage
from utils import mask as packing
from visualization import configs
from visualization.selectors.window import Window


@dataclass(frozen=True, slots=True)
class Grid:
    """What every candidate window of one feature holds.

    Attributes:
        centres: The moment each column's window is centred on, as date
            numbers. A window reaches half its length either side of it.
        widths: How long each row's window lasts, in days, up to the longest
            a cluster is allowed to span.
        reached: The share of the feature's cells a window covers, counted
            evenly over the instruments that observed it as the search counts
            it, one value per width and centre.
        instruments: How many instruments observed the feature inside every
            window, shaped as reached.
        sounded: Whether every window holds a sounder track, which a cluster
            cannot do without, shaped as reached.
    """

    centres: np.ndarray
    widths: np.ndarray
    reached: np.ndarray
    instruments: np.ndarray
    sounded: np.ndarray


def build(coverage: Sequence[SetCoverage], window: Window) -> Grid | None:
    """Score every window the feature's observations could be clustered into.

    Args:
        coverage: The feature's instrument sets, in the order the config names them.
        window: The date range to score inside, which excludes the rest.

    Returns:
        The scored grid, or None when the record is too short to hold a choice
        of windows at all.
    """
    observed = [window.visible(entry.events) for entry in coverage]
    observed = [events for events in observed if events]
    if not observed:
        return None
    moments = np.sort(np.concatenate([_moments(events) for events in observed]))
    span = float(moments[-1] - moments[0])
    if span < configs.WINDOW_MIN_DAYS:
        return None
    centres = np.linspace(moments[0], moments[-1], configs.WINDOW_COLUMNS)
    widths = np.geomspace(
        configs.WINDOW_MIN_DAYS,
        min(span, configs.WINDOW_MAX_DAYS),
        configs.WINDOW_WIDTHS,
    )
    cells = coverage[0].summary.mask_cells
    covered = [_covered(events, cells, centres, widths) for events in observed]
    present = [_counts(events, centres, widths) > 0 for events in observed]
    sounders = [events for events in observed if _sounder(events)]
    return Grid(
        centres=centres,
        widths=widths,
        reached=_evenly(covered),
        instruments=np.sum(present, axis=0),
        sounded=_qualified(sounders, centres, widths),
    )


def _evenly(covered: Sequence[np.ndarray]) -> np.ndarray:
    """Count what the instruments cover the way the search counts it.

    Args:
        covered: What share of the feature each set covers, one array per set.

    Returns:
        The shares multiplied and rooted, so that a window one instrument
        misses reads as the poor window the search takes it for.
    """
    return np.prod(covered, axis=0) ** (1.0 / len(covered))


def _sounder(events: Sequence[Event]) -> bool:
    """Report whether a set sounds a track rather than publishing an area.

    Args:
        events: One instrument set's observations of the feature.

    Returns:
        True when the set's footprints were widened from a bare line, which is
        the only way an observation carries a swath width.
    """
    return any(event.width_km for event in events)


def _qualified(
    sets: Sequence[Sequence[Event]], centres: np.ndarray, widths: np.ndarray
) -> np.ndarray:
    """Mark the windows a sounder flew through at least once.

    Args:
        sets: The observations of every set that sounds a track.
        centres: The moment each column's window is centred on.
        widths: How long each row's window lasts, in days.

    Returns:
        True where a window holds a track, one value per width and centre, and
        False everywhere when no sounder reached the feature at all, since a
        cluster is required to hold one.
    """
    if not sets:
        return np.zeros((widths.size, centres.size), dtype=bool)
    flown = sum(_counts(events, centres, widths) for events in sets)
    return flown > 0


def _moments(events: Sequence[Event]) -> np.ndarray:
    """Return when each of a set's observations started, as date numbers.

    Args:
        events: One instrument set's observations, in chronological order.

    Returns:
        The start times in the same order.
    """
    return date2num([event.t_start for event in events])


def _covered(
    events: Sequence[Event], cells: int, centres: np.ndarray, widths: np.ndarray
) -> np.ndarray:
    """Measure the ground one set covers inside every candidate window.

    Args:
        events: The set's observations, in chronological order.
        cells: How many of the feature's cells fall inside it.
        centres: The moment each column's window is centred on.
        widths: How long each row's window lasts, in days.

    Returns:
        The share of the feature it covers, one value per width and centre.
    """
    starts, previous = _sightings(events)
    moments = _moments(events)
    filled = [
        [
            int((previous[starts[first] : starts[last]] < first).sum())
            for first, last in zip(*_reaching(moments, centres, width), strict=True)
        ]
        for width in widths
    ]
    return np.array(filled) / cells


def _sightings(events: Sequence[Event]) -> tuple[np.ndarray, np.ndarray]:
    """Flatten the set's masks and say where each cell was last seen before.

    A window covers a cell exactly once: at the first entry inside the window
    whose previous sighting falls before it. Counting those entries therefore
    counts distinct cells, which turns every window into one comparison over a
    contiguous slice rather than a fresh union of whole bitmaps.

    Args:
        events: The set's observations, in chronological order.

    Returns:
        Where each observation's cells begin in the flat list, one entry longer
        than there are observations, and for every cell in that list the
        observation that last filled the same cell, or -1 when none did.
    """
    per = [packing.cells_of(event.mask) for event in events]
    counts = np.fromiter((cells.size for cells in per), dtype=np.int64, count=len(per))
    starts = np.zeros(len(per) + 1, dtype=np.int64)
    np.cumsum(counts, out=starts[1:])
    if not starts[-1]:
        return starts, np.zeros(0, dtype=np.int64)
    flat = np.concatenate(per)
    owner = np.repeat(np.arange(len(per), dtype=np.int64), counts)
    order = np.lexsort((owner, flat))
    ranked_cells, ranked_owner = flat[order], owner[order]
    ranked = np.empty(flat.size, dtype=np.int64)
    ranked[0] = -1
    ranked[1:] = np.where(ranked_cells[1:] == ranked_cells[:-1], ranked_owner[:-1], -1)
    previous = np.empty(flat.size, dtype=np.int64)
    previous[order] = ranked
    return starts, previous


def _counts(
    events: Sequence[Event], centres: np.ndarray, widths: np.ndarray
) -> np.ndarray:
    """Count how many of one set's observations fall inside every window.

    Args:
        events: The set's observations, in chronological order.
        centres: The moment each column's window is centred on.
        widths: How long each row's window lasts, in days.

    Returns:
        The count, one value per width and centre.
    """
    moments = _moments(events)
    windows = [_reaching(moments, centres, width) for width in widths]
    return np.array([last - first for first, last in windows])


def _reaching(
    moments: np.ndarray, centres: np.ndarray, width: float
) -> tuple[np.ndarray, np.ndarray]:
    """Find which of a set's observations every window of one length holds.

    Args:
        moments: When the set's observations started, in order.
        centres: The moment each column's window is centred on.
        width: How long the windows last, in days.

    Returns:
        The first and the last index each window holds, as a half open range.
    """
    return (
        np.searchsorted(moments, centres - width / 2.0, side="left"),
        np.searchsorted(moments, centres + width / 2.0, side="right"),
    )

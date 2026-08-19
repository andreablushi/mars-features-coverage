"""Every window a feature's record could be clustered into, and what each holds."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from matplotlib.dates import date2num

from models.results import Event, SetCoverage
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
        reached: The share of the feature a window covers, averaged over the
            instruments that observed it, one value per width and centre.
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

    Coverage accumulates one instrument at a time and the instruments are then
    averaged, since a camera cannot stand in for a spectrometer and the two
    cover their own ground. A set that observed nothing of the feature at all
    is left out of the average, so one silent instrument does not drag every
    window down. A sounder is averaged in like the rest, but it also decides
    whether a window counts at all: a cluster without a track through it is no
    cluster, so a window holding none is disqualified however much it covers.

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
    area_km2 = coverage[0].summary.feature_area_km2
    covered = [_certain(events, centres, widths) for events in observed]
    present = [_counts(events, centres, widths) > 0 for events in observed]
    sounders = [events for events in observed if _sounder(events)]
    return Grid(
        centres=centres,
        widths=widths,
        reached=np.mean(covered, axis=0) / area_km2,
        instruments=np.sum(present, axis=0),
        sounded=_qualified(sounders, centres, widths),
    )


def _sounder(events: Sequence[Event]) -> bool:
    """Report whether a set sounds a track rather than publishing an area.

    Args:
        events: One instrument set's observations of the feature.

    Returns:
        True when the set's footprints were widened from a bare line.
    """
    return any(event.width_source for event in events)


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


def _certain(
    events: Sequence[Event], centres: np.ndarray, widths: np.ndarray
) -> np.ndarray:
    """Measure the ground one set cannot fail to cover inside every window.

    The running union credits an observation only with what nothing before it
    had reached, so a window late in the record is credited with almost
    nothing however much it sees. A window also covers at least the whole of
    its single widest observation, which no earlier window can take away, so
    the greater of the two is what the window is certain to reach.

    Args:
        events: The set's observations, in chronological order.
        centres: The moment each column's window is centred on.
        widths: How long each row's window lasts, in days.

    Returns:
        The square kilometres it covers, one value per width and centre.
    """
    return np.maximum(
        _totals(events, centres, widths, lambda event: event.new_km2 or 0.0),
        _peaks(events, centres, widths),
    )


def _peaks(
    events: Sequence[Event], centres: np.ndarray, widths: np.ndarray
) -> np.ndarray:
    """Find the widest single observation one set has inside every window.

    Args:
        events: The set's observations, in chronological order.
        centres: The moment each column's window is centred on.
        widths: How long each row's window lasts, in days.

    Returns:
        The square kilometres its widest footprint covers, one value per width
        and centre, and zero where the window holds none.
    """
    moments = _moments(events)
    own = np.array([event.own_km2 for event in events])
    return np.array(
        [
            [
                own[first:last].max() if last > first else 0.0
                for first, last in zip(*_reaching(moments, centres, width), strict=True)
            ]
            for width in widths
        ]
    )


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


def _totals(
    events: Sequence[Event],
    centres: np.ndarray,
    widths: np.ndarray,
    value: Callable[[Event], float],
) -> np.ndarray:
    """Add up what one set contributes inside every candidate window.

    Args:
        events: The set's observations, in chronological order.
        centres: The moment each column's window is centred on.
        widths: How long each row's window lasts, in days.
        value: What one observation contributes.

    Returns:
        The total inside each window, one value per width and centre.
    """
    moments = _moments(events)
    running = np.concatenate([[0.0], np.cumsum([value(event) for event in events])])
    windows = [_reaching(moments, centres, width) for width in widths]
    return np.array([running[last] - running[first] for first, last in windows])


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

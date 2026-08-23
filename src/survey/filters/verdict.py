"""Asking a feature everything the dataset asks of it."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import Event, SetCoverage
from survey import algorithm, configs
from survey.models.survey import Survey
from survey.models.track import Track, build
from survey.models.verdict import Verdict
from survey.utils import overlap


def assess(coverage: Sequence[SetCoverage]) -> Verdict:
    """Search an optimal window for a feature and judge whether it is worth keeping.

    Args:
        coverage: The feature's instrument sets, in any order.

    Returns:
        The verdict, holding the window and every count behind it.
    """
    track = build(coverage)
    if track is None:
        return Verdict(
            survey=None,
            gridded=False,
            sounders_refused=0,
            smallest=[],
            refused=0,
            taken=0,
            overlaps={},
        )
    picked = algorithm.search(track)
    return Verdict(
        survey=picked,
        gridded=True,
        sounders_refused=_sounders(track),
        smallest=_smallest(track, picked),
        refused=_refused(track, picked),
        taken=picked.observations if picked else len(track.observations),
        overlaps=_overlaps(track, picked),
    )


def _sounders(track: Track) -> int:
    """Count the sounder tracks that were too small to count.

    Args:
        track: The feature's admissible observations on one time axis.

    Returns:
        How many of the observations left off the axis were sounder tracks.
    """
    return sum(bool(observation.width_km) for observation in track.refused)


def _overlaps(track: Track, picked: Survey | None) -> dict[int, float]:
    """Measure how much ground several instruments reach between them.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window the shared ground is counted inside, or None when
            the search found none.

    Returns:
        The ground in square kilometres reached by at least that many sets, by
        set count, and nothing at all without a window to count it inside.
    """
    if picked is None:
        return {}
    counted = overlap.reached(track, picked)
    return {
        wanted: overlap.ground(counted, wanted, track.cell_km2)
        for wanted in configs.OVERLAP_SETS
    }


def _smallest(track: Track, picked: Survey | None) -> dict[str, Event]:
    """Find the least an instrument's single observation covers in the window.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window the search found, or None when it found none.

    Returns:
        The smallest observation each set left in the window, by set name,
        least ground first, so that whatever the window is thinnest on comes
        first.
    """
    if picked is None:
        return {}
    least: dict[int, Event] = {}
    for owner, observation in zip(track.owners, track.observations, strict=True):
        if picked.start <= observation.t_start <= picked.end:
            held = least.get(owner)
            if held is None or observation.own_km2 < held.own_km2:
                least[owner] = observation
    return {
        track.labels[owner]: observation
        for owner, observation in sorted(
            least.items(), key=lambda found: found[1].own_km2
        )
    }


def _refused(track: Track, picked: Survey | None) -> int:
    """Count what the window turned away for being too small.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window the search found, or None when it found none.

    Returns:
        How many were turned away over that stretch.
    """
    if picked is None:
        return len(track.refused)
    return sum(
        1
        for observation in track.refused
        if picked.start <= observation.t_start <= picked.end
    )

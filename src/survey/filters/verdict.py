"""Asking a feature everything the dataset asks of it."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import SetCoverage
from survey import algorithm, configs
from survey.models.survey import Survey
from survey.models.track import Track, build
from survey.models.verdict import Row, Verdict
from utils.maths import quantities

_NOTHING = "no cells filled"
_UNCOUNTED = "not counted"


def kept(checks: Sequence[Row]) -> bool:
    """Report whether the feature belongs in the dataset.

    Args:
        checks: Everything asked of it.

    Returns:
        True when everything required of it holds. A row there to be read has
        no say in this.
    """
    return all(passed for _, _, _, passed in checks if passed is not None)


def assess(coverage: Sequence[SetCoverage]) -> Verdict:
    """Search one feature for a window, and judge whether it is worth keeping.

    A feature is not kept or dropped on the window alone. A window can be
    found and still be built on too few observations, on one instrument, or on
    a feature the record barely touched, and each of those is a different
    reason to leave it out. Every reason is asked separately and answered in
    full, so a feature that is left out says which rung it failed rather than
    only that it failed.

    The search still runs on a feature that will be left out. What it found is
    worth reading beside the reason it was not kept, and the panels draw it
    either way.

    Args:
        coverage: The feature's instrument sets, in any order.

    Returns:
        The verdict, holding the window, every check, and the counts behind
        them.
    """
    track = build(coverage)
    if track is None:
        return Verdict(None, [("Ground on the feature", _NOTHING, "any", False)])
    picked = algorithm.search(track)
    return Verdict(survey=picked, checks=_checks(track, picked))


def _sounding(track: Track, picked: Survey | None) -> str:
    """Say whether a sounder track was found, and where it went when not.

    A sounder track clipping the edge of a feature is dropped like any other
    observation too small to count, and a feature whose only tracks were that
    small has no survey for a different reason than one no sounder ever flew
    over. The two read alike once the search returns nothing, so the dropped
    tracks are named here.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window the search found, or None when it found none.

    Returns:
        The line the scorecard reads on that row.
    """
    if picked is not None:
        return "found"
    sounded = sum(bool(observation.width_km) for observation in track.refused)
    if sounded:
        return f"none, {sounded:,} tracks were too small to count"
    return "none"


def _checks(track: Track, picked: Survey | None) -> list[Row]:
    """Ask a feature everything the dataset asks of it.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window the search found, or None when it found none.

    Returns:
        Every row, the required ones first and what is only worth reading last.
    """
    rows = [
        (
            "A window holding a sounder track",
            _sounding(track, picked),
            "one",
            picked is not None,
        ),
    ]
    if picked is not None:
        rows += [
            (
                "Instruments in the window",
                f"{picked.instruments}",
                f"{configs.MIN_SETS}",
                picked.instruments >= configs.MIN_SETS,
            ),
            (
                "Observations bringing ground of their own",
                f"{picked.core:,} of {picked.observations:,}",
                "",
                None,
            ),
            (
                "Ground the window reaches, counted evenly",
                f"{picked.reach:.0%} over {quantities.duration(picked.days)}",
                "",
                None,
            ),
        ]
        rows += [
            (
                f"Smallest observation from {label}",
                reads,
                "",
                None,
            )
            for _, reads, label in _smallest(track, picked)
        ]
    rows.append(
        (
            "Observations too small to count",
            _refused(track, picked),
            "",
            None,
        )
    )
    return rows


def _smallest(track: Track, picked: Survey) -> list[tuple[float, str, str]]:
    """Find the least an instrument's single observation covers in the window.

    This is what the floors are read against. Every observation here already
    cleared them, so the smallest one says how close to the floor the window
    is actually working, and whether there is anything in it worth turning
    away that is not being turned away.

    A set the window never holds has no smallest observation and is left out,
    since it has none to answer with.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window the search found.

    Both the ground and the pixels it landed there are given, since they are
    the two floors an observation is asked to clear and one does not follow
    from the other: a pixel is a quarter of a metre across for HiRISE and more
    than a kilometre for SHARAD.

    Returns:
        The ground, what it reads as with its pixels, and the instrument, least
        first, so that whatever the window is thinnest on is read first.
    """
    least: dict[int, tuple[float, float | None]] = {}
    for owner, observation in zip(track.owners, track.observations, strict=True):
        if picked.start <= observation.t_start <= picked.end:
            held = least.get(owner)
            if held is None or observation.own_km2 < held[0]:
                least[owner] = (observation.own_km2, observation.pixels)
    return sorted(
        (ground, _measured(ground, pixels), track.labels[owner])
        for owner, (ground, pixels) in least.items()
    )


def _measured(ground: float, pixels: float | None) -> str:
    """Write one observation's size in both of the units it is judged in.

    Args:
        ground: How much of the feature it covers, in square kilometres.
        pixels: How many of the instrument's pixels it landed there, or None
            when the artifact predates the measurement.

    Returns:
        The ground and the pixels, or the ground alone where none were counted.
    """
    if pixels is None:
        return f"{quantities.area(ground)}, pixels {_UNCOUNTED}"
    return f"{quantities.area(ground)}, {quantities.compact(pixels)} pixels"


def _refused(track: Track, picked: Survey | None) -> str:
    """Count what the window turned away, out of everything taken during it.

    The count is of the window and not of the record, since what a stretch of
    time elsewhere had to leave out says nothing about the stretch that was
    chosen. A feature with no window at all is counted over its whole record,
    which is the only span it has.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window the search found, or None when it found none.

    Returns:
        How many were turned away, out of how many were taken.
    """
    if picked is None:
        turned, taken = len(track.refused), len(track.observations)
        return f"{turned:,} of {turned + taken:,}"
    inside = sum(
        1
        for observation in track.refused
        if picked.start <= observation.t_start <= picked.end
    )
    return f"{inside:,} of {inside + picked.observations:,}"

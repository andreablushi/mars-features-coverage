"""Whether a feature earns a place in the dataset, and what decided it."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from campaign import algorithm, configs, timeline
from campaign.results import Campaign
from campaign.timeline import Filter, Track
from models.results import SetCoverage
from utils import quantities

_NOTHING = "no cells filled"
_UNCOUNTED = "not counted"


@dataclass(frozen=True, slots=True)
class Check:
    """One thing asked of a feature, and what the feature answered.

    Attributes:
        name: What is being asked of it.
        value: What it holds, written to be read.
        wanted: The least it can hold and still pass, or an empty string when
            the row is there to be read rather than to be met.
        passed: Whether it holds it.
        required: Whether failing this alone keeps the feature out.
    """

    name: str
    value: str
    wanted: str
    passed: bool
    required: bool = True


@dataclass(frozen=True, slots=True)
class Verdict:
    """Whether one feature belongs in the dataset, and everything behind it.

    Attributes:
        campaign: The window the search picked, or None when it found none.
        checks: Everything asked of the feature, in the order they read.
    """

    campaign: Campaign | None
    checks: list[Check]

    @property
    def kept(self) -> bool:
        """Report whether the feature belongs in the dataset.

        Returns:
            True when everything required of it holds. A row that is there to
            be read has no say in this.
        """
        return all(check.passed for check in self.checks if check.required)


def assess(coverage: Sequence[SetCoverage], visible: Filter | None = None) -> Verdict:
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
        visible: A filter narrowing each set to the observations to consider,
            or None to judge it on the whole record.

    Returns:
        The verdict, holding the window, every check, and the counts behind
        them.
    """
    track = timeline.build(coverage, visible)
    if track is None:
        return Verdict(None, [Check("Ground on the feature", _NOTHING, "any", False)])
    picked = algorithm.search(track)
    return Verdict(campaign=picked, checks=_checks(track, picked))


def _sounding(track: Track, picked: Campaign | None) -> str:
    """Say whether a sounder track was found, and where it went when not.

    A sounder track clipping the edge of a feature is dropped like any other
    observation too small to count, and a feature whose only tracks were that
    small has no campaign for a different reason than one no sounder ever flew
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
    if track.sounded:
        return f"none, {track.sounded:,} tracks were too small to count"
    return "none"


def _checks(track: Track, picked: Campaign | None) -> list[Check]:
    """Ask a feature everything the dataset asks of it.

    Args:
        track: The feature's admissible observations on one time axis.
        picked: The window the search found, or None when it found none.

    Returns:
        Every check, the required ones first and what is only worth reading
        last.
    """
    rows = [
        Check(
            "A window holding a sounder track",
            _sounding(track, picked),
            "one",
            picked is not None,
        ),
    ]
    if picked is not None:
        rows += [
            Check(
                "Instruments in the window",
                f"{picked.instruments}",
                f"{configs.MIN_SETS}",
                picked.instruments >= configs.MIN_SETS,
            ),
            Check(
                "Observations bringing ground of their own",
                f"{picked.core:,} of {picked.observations:,}",
                "",
                True,
                required=False,
            ),
            Check(
                "Ground the window reaches, counted evenly",
                f"{picked.reach:.0%} over {picked.length}",
                "",
                True,
                required=False,
            ),
        ]
        rows += [
            Check(
                f"Smallest observation from {label}",
                reads,
                "",
                True,
                required=False,
            )
            for _, reads, label in _smallest(track, picked)
        ]
    rows.append(
        Check(
            "Observations too small to count",
            _refused(track, picked),
            "",
            True,
            required=False,
        )
    )
    return rows


def _smallest(track: Track, picked: Campaign) -> list[tuple[float, str, str]]:
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
    inside = zip(track.owners, track.moments, track.grounds, track.pixels, strict=True)
    for owner, taken, ground, pixels in inside:
        if picked.start <= taken <= picked.end:
            held = least.get(owner)
            if held is None or ground < held[0]:
                least[owner] = (ground, pixels)
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


def _refused(track: Track, picked: Campaign | None) -> str:
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
        return f"{len(track.refused):,} of {len(track.refused) + track.size:,}"
    inside = sum(1 for taken in track.refused if picked.start <= taken <= picked.end)
    return f"{inside:,} of {inside + picked.observations:,}"

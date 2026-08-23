"""Reading a verdict's counts back as the lines the scorecard is written in."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from models.results import Event
from survey import configs
from survey.models.survey import Survey
from survey.models.verdict import Verdict
from utils.maths import quantities

Row = tuple[str, str, str, bool | None]

_NOTHING = "no cells filled"
_UNCOUNTED = "not counted"
_NONE = "none"

# What each count of instruments is called in the shared ground rows.
_WORDS = {3: "three", 2: "two"}


def rows(verdict: Verdict, area_km2: float) -> list[Row]:
    """Write out everything the feature was asked and everything it answered.

    A feature is searched a tile at a time and only the tiles that earned a
    window are kept, so the one thing asked of the feature as a whole is how
    many of them did. Every other row is there to say what those tiles hold.

    Args:
        verdict: What the feature was judged to be.
        area_km2: How much ground the feature covers, which the ground the
            tiles hold is read back as a share of.

    Returns:
        Every row, the one that decides it first and what is only worth
        reading after. Each is what was asked, what it holds, the least it
        could hold and still pass, and whether it passed, which is None on a
        row that is there to be read rather than to be met.
    """
    if not verdict.gridded:
        return [("Ground on the feature", _NOTHING, "any", False)]
    written: list[Row] = [
        (
            "Tiles leaving a window worth keeping",
            _emitted(verdict),
            f"{configs.MIN_TILES}",
            verdict.kept,
        )
    ]
    written += _windows(verdict, area_km2)
    written += _overlaps(verdict, area_km2)
    written += [
        (f"Smallest observation from {label}", _measured(least), "", None)
        for label, least in verdict.smallest.items()
    ]
    written.append(
        (
            "Observations too small to count",
            f"{verdict.refused:,} of {verdict.refused + verdict.taken:,}, "
            f"counted tile by tile",
            "",
            None,
        )
    )
    return written


def _emitted(verdict: Verdict) -> str:
    """Say how many tiles earned a window, and what stopped them when none did.

    Args:
        verdict: What the feature was judged to be.

    Returns:
        The line the scorecard reads on that row.
    """
    if verdict.surveys:
        return f"{len(verdict.surveys):,} of {verdict.tiles:,}"
    if verdict.sounders_refused:
        return f"none, {verdict.sounders_refused:,} tracks were too small to count"
    return _NONE


def _windows(verdict: Verdict, area_km2: float) -> list[Row]:
    """Read what the tiles that earned a window hold between them.

    Args:
        verdict: What the feature was judged to be.
        area_km2: How much ground the feature covers.

    Returns:
        One row per thing worth knowing about them, each there to be read
        rather than to be met, and nothing at all when no tile earned one.
    """
    found = verdict.surveys
    if not found:
        return []
    ground = sum(survey.area_km2 for survey in found)
    return [
        (
            "Ground those tiles cover",
            f"{quantities.area(ground)}, {ground / area_km2:.0%} of the feature",
            "",
            None,
        ),
        ("How long their windows last", _spread(found), "", None),
        (
            "Ground a window reaches, counted evenly",
            f"{statistics.median(survey.reach for survey in found):.0%} in the middle "
            f"tile",
            "",
            None,
        ),
        (
            "Observations bringing ground of their own",
            f"{sum(survey.core for survey in found):,} of {verdict.taken:,}, "
            f"counted tile by tile",
            "",
            None,
        ),
    ]


def _spread(found: Sequence[Survey]) -> str:
    """Write how long the windows last, and how much they differ.

    Args:
        found: The windows the tiles earned.

    Returns:
        The middle window's length, and the shortest and longest beside it
        where the tiles do not all agree.
    """
    days = sorted(survey.days for survey in found)
    middle = quantities.duration(statistics.median(days))
    if days[0] == days[-1]:
        return middle
    return (
        f"{middle}, {quantities.duration(days[0])} to {quantities.duration(days[-1])}"
    )


def _overlaps(verdict: Verdict, area_km2: float) -> list[Row]:
    """Read how much ground several instruments reach between them.

    Args:
        verdict: What the feature was judged to be.
        area_km2: How much ground the feature covers, which the ground shared
            is read back as a share of.

    Returns:
        One row per count of instruments, each there to be read rather than to
        be met.
    """
    return [
        (
            f"Ground at least {_WORDS.get(wanted, str(wanted))} instruments reach",
            f"{quantities.area(shared)}, {shared / area_km2:.0%} of the feature",
            "",
            None,
        )
        for wanted, shared in verdict.overlaps.items()
    ]


def _measured(least: Event) -> str:
    """Write one observation's size in both of the units it is judged in.

    Args:
        least: The smallest observation one instrument set left in a window.

    Returns:
        The ground and the pixels, or the ground alone where none were counted.
    """
    ground = quantities.area(least.own_km2)
    if least.pixels is None:
        return f"{ground}, pixels {_UNCOUNTED}"
    return f"{ground}, {quantities.compact(least.pixels)} pixels"

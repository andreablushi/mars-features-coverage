"""Reading a verdict's counts back as the lines the scorecard is written in."""

from __future__ import annotations

from models.results import Event
from survey import configs
from survey.models.verdict import Verdict
from utils.maths import quantities

Row = tuple[str, str, str, bool | None]

_NOTHING = "no cells filled"
_UNCOUNTED = "not counted"

# What each count of instruments is called in the shared ground rows.
_WORDS = {3: "three", 2: "two"}


def rows(verdict: Verdict, area_km2: float) -> list[Row]:
    """Write out everything the feature was asked and everything it answered.

    Args:
        verdict: What the feature was judged to be.
        area_km2: How much ground the feature covers, which the shares of it
            are read back in.

    Returns:
        Every row, the required ones first and what is only worth reading
        last. Each is what was asked, what it holds, the least it could hold
        and still pass, and whether it passed, which is None on a row that is
        there to be read rather than to be met.
    """
    if not verdict.gridded:
        return [("Ground on the feature", _NOTHING, "any", False)]
    picked = verdict.survey
    written: list[Row] = [
        (
            "A window holding a sounder track",
            _sounding(verdict),
            "one",
            picked is not None,
        ),
    ]
    if picked is not None:
        written += [
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
        written += _overlaps(verdict, area_km2)
        written += [
            (f"Smallest observation from {label}", _measured(least), "", None)
            for label, least in verdict.smallest.items()
        ]
    written.append(
        (
            "Observations too small to count",
            f"{verdict.refused:,} of {verdict.refused + verdict.taken:,}",
            "",
            None,
        )
    )
    return written


def _sounding(verdict: Verdict) -> str:
    """Say whether a sounder track was found, and where it went when not.

    Args:
        verdict: What the feature was judged to be.

    Returns:
        The line the scorecard reads on that row.
    """
    if verdict.survey is not None:
        return "found"
    if verdict.sounders_refused:
        return f"none, {verdict.sounders_refused:,} tracks were too small to count"
    return "none"


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
        least: The smallest observation one instrument set left in the window.

    Returns:
        The ground and the pixels, or the ground alone where none were counted.
    """
    ground = quantities.area(least.own_km2)
    if least.pixels is None:
        return f"{ground}, pixels {_UNCOUNTED}"
    return f"{ground}, {quantities.compact(least.pixels)} pixels"

"""The feature on show, and everything the search left on it."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.sampling import measuring
from analysis.sampling.models.feature import FeatureStats
from analysis.utils.maths import quantities
from analysis.visualization.common import panels, surveys, tables, wording
from analysis.visualization.common.picker import View
from analysis.visualization.common.tables import Row

_HEADINGS = ("On this feature", "What it holds")
_NOTHING = "No instrument set filled a cell of this feature."
_NONE = "-"


def plot(view: View) -> widgets.Widget:
    """Summarise what the search left on the feature on show.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The table as a widget, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    stats = measuring.measured_feature(surveys.studied(view.coverage, view.strategy))
    if stats is None:
        return panels.unavailable(_NOTHING)
    return tables.written(
        f"{panels.title(view.coverage)}  -  what it holds", _HEADINGS, _rows(stats)
    )


def _rows(stats: FeatureStats) -> list[Row]:
    """Write out everything the feature holds.

    Args:
        stats: The feature, as the search left it.

    Returns:
        Every row, the feature itself first and what each instrument left last.
    """
    written: list[Row] = [
        ("Ground the feature covers", quantities.area(stats.area_km2)),
        ("How long its window lasts", _window(stats)),
        ("Ground its window reaches", f"{stats.geo_mean:.0%}" if stats.kept else _NONE),
        (
            "Looks too small inside the window",
            f"{stats.refused:,}, with {stats.turned_away:,} too small for the "
            f"feature at all",
        ),
        (
            "Pixels its window holds",
            wording.pixels(_pixels(stats)) if stats.kept else _NONE,
        ),
    ]
    written += [
        (f"Ground {iid} reaches", _reach(stats, iid)) for iid in sorted(stats.reached)
    ]
    written += [
        (
            f"Ground reached by {wording.counted(shared, 'instrument')}",
            wording.ground(km2, stats.area_km2),
        )
        for shared, km2 in measuring.ground_by_instrument_count(stats.overlaps).items()
    ]
    return written


def _window(stats: FeatureStats) -> str:
    """Say how long the feature's window lasts and when it is open.

    Args:
        stats: The feature, as the search left it.

    Returns:
        The length and the dates, or that the feature earned no window.
    """
    if not stats.kept or stats.start is None or stats.end is None:
        return _NONE
    return (
        f"{quantities.duration(stats.days)}, "
        f"{stats.start:%Y-%m-%d} to {stats.end:%Y-%m-%d}"
    )


def _reach(stats: FeatureStats, iid: str) -> str:
    """Write what one instrument left on the feature.

    Args:
        stats: The feature, as the search left it.
        iid: The instrument the row is written for.

    Returns:
        The share of the feature it reaches, its pixels, and how many it keeps.
    """
    reach = stats.reached[iid]
    share = f"{reach.km2 / stats.area_km2:.0%}" if stats.area_km2 else wording.NOTHING
    taken = wording.counted(reach.observations_taken, "observation")
    return f"{share}, {wording.pixels(reach.pixels)}, from {taken}"


def _pixels(stats: FeatureStats) -> float | None:
    """Add up the pixels the feature keeps.

    Args:
        stats: The feature, as the search left it.

    Returns:
        The total, or None when any instrument carries no count.
    """
    counted = [reach.pixels for reach in stats.reached.values()]
    if any(count is None for count in counted):
        return None
    return sum(count for count in counted if count is not None)

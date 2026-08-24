"""The feature on show, averaged over every tile the search ran over."""

from __future__ import annotations

import ipywidgets as widgets

from visualization.common import panels, surveys, tables, tiles, wording
from visualization.common.aggregate import Aggregate
from visualization.common.picker import View
from visualization.common.tables import Row
from visualization.feature.stats import whole
from visualization.feature.stats.whole import FeatureStats

_HEADINGS = ("Across the tiles", "What they hold")
_NOTHING = "No instrument set filled a cell of this feature."
_NOTE = "Every average is taken over the tiles that earned a window."


def plot(view: View) -> widgets.Widget:
    """Summarise what the feature holds across the tiles it was searched over.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The table as a widget, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    study = surveys.studied(view.coverage, view.strategy)
    if not study.gridded:
        return panels.unavailable(_NOTHING)
    stats = whole.read(
        study, tiles.measured(study), view.coverage[0].summary.feature_area_km2
    )
    return tables.written(
        f"{panels.title(view.coverage)}  -  across its tiles",
        _HEADINGS,
        _rows(stats),
        lead=f"searched under {view.strategy.name}",
        note=_NOTE,
    )


def _rows(stats: FeatureStats) -> list[Row]:
    """Write out everything the feature holds between its tiles.

    Args:
        stats: The feature read across them.

    Returns:
        Every row, the tiles first and what they hold after.
    """
    held = stats.held
    written: list[Row] = [
        ("Tiles searched", f"{held.searched:,} of {stats.tiles:,} holding feature"),
        ("Tiles earning a window", f"{held.kept:,} of {held.searched:,}"),
        ("Ground those tiles cover", wording.ground(held.kept_km2, stats.feature_km2)),
        ("How long a window lasts", wording.span(held.days)),
        ("Ground a window reaches", wording.share(held.reach)),
    ]
    written += _observations(held)
    written += [
        (
            f"Ground {iid} reaches, per tile",
            f"{wording.share(held.reached[iid])}, {wording.pixels(held.pixels[iid])}",
        )
        for iid in stats.iids
    ]
    written += [
        (
            f"Ground {' and '.join(names)} reach",
            wording.ground(km2, stats.feature_km2),
        )
        for names, km2 in held.overlaps.items()
    ]
    return written


def _observations(held: Aggregate) -> list[Row]:
    """Write what became of the observations the tiles were offered.

    Args:
        held: The tiles read as one.

    Returns:
        One row per fate an observation could meet, counted tile by tile.
    """
    offered = held.taken + held.dropped
    return [
        (
            "Observations bringing ground of their own",
            f"{held.taken:,} of {offered:,}",
        ),
        (
            "Looks too small inside a window",
            f"{held.refused:,}, with {held.turned_away:,} too small for a tile at all",
        ),
        (
            "Pixels the windows hold",
            wording.pixels(_pixels(held)),
        ),
    ]


def _pixels(held: Aggregate) -> float | None:
    """Add up the pixels every instrument landed inside the windows.

    Args:
        held: The tiles read as one.

    Returns:
        The total, or None when any instrument carries no count.
    """
    counted = list(held.pixels.values())
    if any(count is None for count in counted):
        return None
    return sum(count for count in counted if count is not None)

"""The feature on show, and everything the search left on it."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.stats.feature import measuring, reading
from analysis.utils.maths import quantities
from analysis.visualization.common import panels, tables, wording
from analysis.visualization.common.picker import Coverage
from analysis.visualization.common.tables import Row

_HEADINGS = ("On this feature", "What it holds")
_NOTHING = "No instrument set filled a cell of this feature."
_NONE = "-"


def plot(coverage: Coverage) -> widgets.Widget:
    """Summarise what the search left on the feature on show.

    Args:
        coverage: The feature on show, as the instrument sets it holds.

    Returns:
        The table as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    looks = reading.read_feature(coverage)
    if looks is None:
        return panels.unavailable(_NOTHING)
    stats = measuring.measured_feature(looks)
    window = looks.window
    # A window it earned always says when it opened, so only a refusal reads as none
    lasted = (
        f"{quantities.duration(window.days)}, "
        f"{window.start:%Y-%m-%d} to {window.end:%Y-%m-%d}"
        if window.kept
        else _NONE
    )
    counted = [reach.pixels for reach in stats.reached.values()]
    held = None if any(count is None for count in counted) else sum(counted)
    rows: list[Row] = [
        ("Ground the feature covers", quantities.area(window.area_km2)),
        ("How long its window lasts", lasted),
        (
            "Ground its window reaches",
            f"{window.geo_mean:.0%}" if window.kept else _NONE,
        ),
        (
            "Looks too small inside the window",
            f"{stats.refused:,}, with {stats.turned_away:,} too small for the "
            f"feature at all",
        ),
        ("Pixels its window holds", wording.pixels(held) if window.kept else _NONE),
    ]
    for iid in sorted(stats.reached):
        reach = stats.reached[iid]
        taken = wording.counted(reach.observations_taken, "observation")
        rows.append(
            (
                f"Ground {iid} reaches",
                f"{reach.km2 / window.area_km2:.0%}, "
                f"{wording.pixels(reach.pixels)}, from {taken}",
            )
        )
    rows += [
        (
            f"Ground reached by {wording.counted(shared, 'instrument')}",
            wording.ground(km2, window.area_km2),
        )
        for shared, km2 in measuring.ground_by_instrument_count(stats.overlaps).items()
    ]
    return tables.written(
        f"{panels.title(coverage)}  -  what it holds", _HEADINGS, rows
    )

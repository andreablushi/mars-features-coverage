"""How the feature on show is tiled, and what its tiles hold between them."""

from __future__ import annotations

import ipywidgets as widgets

from visualization.common import panels, surveys, tables, tiles, wording
from visualization.common.picker import View
from visualization.common.tables import Row
from visualization.feature.stats import whole
from visualization.feature.stats.whole import FeatureStats

_HEADINGS = ("Statistic", "Value")
_NOTHING = "No instrument set filled a cell of this feature."


def plot(view: View) -> widgets.Widget:
    """Summarise how the feature is tiled and what its tiles hold.

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
    )


def _rows(stats: FeatureStats) -> list[Row]:
    """Write out how the feature is tiled and what its tiles hold.

    Args:
        stats: The feature read across them.

    Returns:
        Every row, the tiling first, what each instrument reaches after it,
        and where the instruments meet last.
    """
    held = stats.held
    written: list[Row] = [
        ("Tiles Holding Feature", f"{stats.tiles:,}"),
        ("Tiles Kept", f"{held.kept:,}"),
    ]
    for iid in stats.iids:
        written += [
            (f"{iid} Ground Mean Across Tiles", wording.share(held.reached[iid])),
            (f"{iid} Pixel Mean Across Tiles", wording.landed(held.landed[iid])),
        ]
    written += [
        (_overlap(counted), wording.ground(km2, held.kept_km2))
        for counted, km2 in tiles.shared(held.overlaps).items()
    ]
    return written


def _overlap(counted: int) -> str:
    """Name the row holding the ground one number of instruments shares.

    Args:
        counted: How many instruments reach that ground at once.

    Returns:
        The row's name.
    """
    return f"Ground Reached By {counted} Instrument{'' if counted == 1 else 's'}"

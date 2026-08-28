"""How the feature on show is tiled, and what its tiles hold between them."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets

from sampling import aggregating, measuring
from sampling.models.tiles import Aggregate
from visualization.common import panels, surveys, tables, wording
from visualization.common.picker import View
from visualization.common.tables import Row

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
    if not study.grid.tiles:
        return panels.unavailable(_NOTHING)
    iids = measuring.instruments_searched(study)
    return tables.written(
        f"{panels.title(view.coverage)}  -  across its tiles",
        _HEADINGS,
        _rows(
            aggregating.aggregate_tiles(measuring.measured_tiles(study), iids),
            measuring.tiles_holding_feature(study),
            iids,
        ),
    )


def _rows(held: Aggregate, holding: int, iids: Sequence[str]) -> list[Row]:
    """Write out how the feature is tiled and what its tiles hold.

    Args:
        held: Its tiles read as one.
        holding: How many tiles hold any of the feature.
        iids: The instruments reported on, in the order they are drawn.

    Returns:
        Every row, the tiling first, then each instrument, then where they meet.
    """
    written: list[Row] = [
        ("Tiles Holding Feature", f"{holding:,}"),
        ("Tiles Kept", f"{held.kept:,}"),
    ]
    for iid in iids:
        written += [
            (f"{iid} Ground Mean Across Tiles", wording.share(held.reached[iid])),
            (f"{iid} Pixel Mean Across Tiles", wording.landed(held.landed[iid])),
        ]
    written += [
        (
            f"Ground Reached By {wording.counted(counted, 'Instrument')}",
            wording.ground(km2, held.kept_km2),
        )
        for counted, km2 in measuring.ground_by_instrument_count(held.overlaps).items()
    ]
    return written

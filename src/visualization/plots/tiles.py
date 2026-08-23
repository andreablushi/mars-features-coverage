"""Which patches of the feature earned a window, and when each of them was seen."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, date2num
from matplotlib.patches import Patch

from models.results import SetCoverage
from survey.models.verdict import Verdict
from utils.maths import quantities
from visualization import panels, surveys

# How large the map of tiles is drawn.
TILE_FIGURE_SIZE = (7.5, 6.5)

# How a tile that earned no window is drawn.
TILE_EMPTY = "#e0e0e0"
TILE_EDGE = "#ffffff"

_NOTHING = "This feature holds no tile any window is worth keeping over."
_UNEARNED = "no window worth keeping"
_MIDDLE = "the tile's window opens here"


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Map the feature's tiles by when the window each of them earned falls.

    A feature wider than a tile is searched a patch at a time, and the patches
    rarely agree: one was imaged and sounded together years before its
    neighbour was. The map is that disagreement, drawn where it happened.

    Args:
        coverage: The feature's instrument sets, in the order the config names
            them.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    verdict = surveys.assessed(coverage)
    if not verdict.surveys:
        return panels.unavailable(_NOTHING)
    figure, axis = plt.subplots(figsize=TILE_FIGURE_SIZE)
    mesh = _field(axis, verdict)
    axis.set_title(
        f"{panels.title(coverage)}  -  when each tile was surveyed",
        fontsize=12,
        loc="left",
    )
    bar = figure.colorbar(mesh, ax=axis, pad=0.02, format=DateFormatter("%Y-%m"))
    bar.set_label(_MIDDLE, fontsize=9)
    bar.ax.tick_params(labelsize=8)
    figure.tight_layout()
    return panels.rendered(figure)


def _field(axis: Axes, verdict: Verdict):
    """Draw one square per tile, coloured by when its window opens.

    Args:
        axis: The panel to draw on.
        verdict: What the feature was judged to be.

    Returns:
        The mesh, for the colour bar to read its colours from.
    """
    opened = np.full((verdict.across, verdict.across), np.nan)
    for survey in verdict.surveys:
        row, column = divmod(survey.tile, verdict.across)
        opened[row, column] = date2num(survey.start)
    colours = plt.get_cmap(panels.COLORMAP).with_extremes(bad=TILE_EMPTY)
    mesh = axis.pcolormesh(
        np.ma.masked_invalid(opened),
        cmap=colours,
        edgecolors=TILE_EDGE,
        linewidth=0.5,
    )
    axis.set_aspect("equal")
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_xlabel(_across(verdict), fontsize=9)
    if len(verdict.surveys) < verdict.tiles:
        axis.legend(
            handles=[Patch(facecolor=TILE_EMPTY, label=_UNEARNED)],
            fontsize=8,
            loc="upper right",
            bbox_to_anchor=(1.0, -0.02),
            frameon=False,
        )
    return mesh


def _across(verdict: Verdict) -> str:
    """Say how the feature was cut up and how much of it was kept.

    Args:
        verdict: What the feature was judged to be.

    Returns:
        The line under the map, north up and west left as the grid is laid.
    """
    ground = sum(survey.area_km2 for survey in verdict.surveys)
    return (
        f"{len(verdict.surveys):,} of {verdict.tiles:,} tiles kept, "
        f"{quantities.area(ground)} in all, north up"
    )

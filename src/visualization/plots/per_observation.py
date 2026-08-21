"""What each single observation covered, at the time it was taken."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from models.results import SetCoverage
from visualization import panels, surveys

# One stacked panel per instrument set, so the height is per panel
PANEL_HEIGHT = 2.5


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Draw one stacked panel per instrument set, sharing both axes.

    Args:
        coverage: The feature's instrument sets, widest coverage first.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    picked = surveys.picked(coverage)
    colours = panels.colours(coverage)
    area_km2 = coverage[0].summary.feature_area_km2
    figure, axes = plt.subplots(
        len(coverage),
        1,
        figsize=(panels.FIGURE_WIDTH, PANEL_HEIGHT * len(coverage)),
        sharex=True,
        sharey=True,
    )
    axes = np.atleast_1d(axes)
    for axis, instrument in zip(axes, coverage, strict=True):
        _panel(axis, instrument, colours[instrument.label], area_km2)
        if picked:
            panels.bracket(axis, picked.start, picked.end)
    _key(axes[0], picked)
    axes[0].set_ylim(-0.05, 1.05)
    axes[0].set_title(
        f"{panels.title(coverage)}  -  coverage per observation",
        fontsize=12,
        loc="left",
    )
    axes[-1].set_xlabel("Observation start time")
    figure.supylabel("Share of the feature covered by one observation", fontsize=10)
    figure.tight_layout()
    return panels.rendered(figure)


def _panel(axis, instrument: SetCoverage, colour, area_km2: float) -> None:
    """Draw one instrument set's observations on its own panel.

    Args:
        axis: The panel to draw on.
        instrument: The instrument set being drawn.
        colour: The colour the set is drawn in.
        area_km2: The feature's bounding box area, which the heights are a share of.

    Returns:
        None.
    """
    times = [observation.t_start for observation in instrument.events]
    shares = [observation.own_km2 / area_km2 for observation in instrument.events]
    axis.vlines(times, 0.0, shares, color=colour, alpha=0.35, linewidth=0.7)
    axis.scatter(
        times, shares, s=12, alpha=0.65, color=colour, edgecolors="none", zorder=3
    )
    if not instrument.observed:
        axis.text(
            0.5,
            0.5,
            instrument.reason,
            transform=axis.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            color=panels.GREY,
        )
    axis.set_ylabel(instrument.label, rotation=0, ha="right", va="center", fontsize=9)
    panels.tidy(axis, percent="y", grid="y")


def _key(axis, picked) -> None:
    """Name the marked stretch of time, when the search found one.

    Args:
        axis: The top panel, which carries the legend.
        picked: The window the search chose, or None when it found none.

    Returns:
        None.
    """
    if not picked:
        return
    marker = Line2D(
        [],
        [],
        color=panels.SURVEY_LINE,
        linestyle=panels.SURVEY_STYLE,
        linewidth=panels.SURVEY_WIDTH,
        label=panels.caption(picked),
    )
    axis.legend(handles=[marker], fontsize=8, loc="upper right", frameon=False)

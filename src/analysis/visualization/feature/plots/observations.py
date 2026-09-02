"""What each single observation covered, at the time it was taken."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from analysis.visualization.common import panels, series, surveys
from analysis.visualization.common.picker import Coverage
from analysis.visualization.common.series import Series
from analysis.visualization.common.surveys import Stretch

# One stacked panel per instrument set, so the height is per panel
PANEL_HEIGHT = 2.5

_GROUND = "Share of the feature covered by one observation"


def plot(coverage: Coverage) -> widgets.Widget:
    """Draw one stacked panel per instrument set, over the whole feature.

    Every observation ODE published is drawn, including the ones the search
    turned away as too small, and the window it chose is shaded across them.

    Args:
        coverage: The feature on show, as the instrument sets it holds.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    study = surveys.studied(coverage)
    return _draw(
        series.over_feature(coverage),
        f"{panels.title(coverage)}  -  coverage per observation",
        surveys.open_for(study),
        study.criteria.timeless,
    )


def _draw(
    drawn: Sequence[Series],
    title: str,
    open_for: Sequence[Stretch],
    timeless: frozenset[str],
) -> widgets.Widget:
    """Draw one stacked panel per instrument set, sharing both axes.

    Args:
        drawn: What each set observed of the feature.
        title: The line above the top panel.
        open_for: The stretch of time the window is open over.
        timeless: The instruments the strategy asks of the whole record.

    Returns:
        The figure as a widget.
    """
    colours = panels.colours([one.label for one in drawn])
    figure, axes = plt.subplots(
        len(drawn),
        1,
        figsize=(panels.FIGURE_WIDTH, PANEL_HEIGHT * len(drawn)),
        sharex=True,
        sharey=True,
    )
    axes = np.atleast_1d(axes)
    marked = False
    for axis, one in zip(axes, drawn, strict=True):
        _panel(axis, one, colours[one.label])
        if one.iid not in timeless:
            panels.shade(axis, open_for)
            marked = True
    _key(axes[0], open_for if marked else [])
    if not any(one.observed for one in drawn):
        axes[0].set_xlim(
            min(one.first for one in drawn), max(one.last for one in drawn)
        )
    axes[0].set_ylim(-0.05, 1.05)
    axes[0].set_title(title, fontsize=12, loc="left")
    axes[-1].set_xlabel("Observation start time")
    figure.supylabel(_GROUND, fontsize=10)
    figure.tight_layout()
    return panels.rendered(figure)


def _panel(axis, one: Series, colour) -> None:
    """Draw one instrument set's observations on its own panel.

    Args:
        axis: The panel to draw on.
        one: What the set observed.
        colour: The colour the set is drawn in.

    Returns:
        None.
    """
    axis.vlines(one.times, 0.0, one.shares, color=colour, alpha=0.35, linewidth=0.7)
    axis.scatter(
        one.times,
        one.shares,
        s=12,
        alpha=0.65,
        color=colour,
        edgecolors="none",
        zorder=3,
    )
    if not one.observed:
        panels.note(axis, one.reason)
    axis.set_ylabel(one.label, rotation=0, ha="right", va="center", fontsize=9)
    panels.tidy(axis, percent="y", grid="y")


def _key(axis, open_for: Sequence[Stretch]) -> None:
    """Name the marked stretch of time, when the feature earned one.

    Args:
        axis: The top panel, which carries the legend.
        open_for: The stretch of time the window is open over.

    Returns:
        None.
    """
    if not open_for:
        return
    marker = Line2D(
        [],
        [],
        color=panels.SURVEY_LINE,
        linestyle=panels.SURVEY_STYLE,
        linewidth=panels.SURVEY_WIDTH,
        label="the window the feature earned",
    )
    axis.legend(handles=[marker], fontsize=8, loc="upper right", frameon=False)

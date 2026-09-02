"""What each single observation covered, at the time it was taken."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from analysis.visualization.common import panels, series
from analysis.visualization.common.picker import View
from analysis.visualization.common.series import Series
from analysis.visualization.common.surveys import Stretch
from analysis.visualization.feature.picker import NO_TILE, TileView

# One stacked panel per instrument set, so the height is per panel
PANEL_HEIGHT = 2.5

_FEATURE_GROUND = "Share of the feature covered by one observation"
_TILE_GROUND = "Share of the tile covered by one observation"


def plot(view: View) -> widgets.Widget:
    """Draw one stacked panel per instrument set, over the whole feature.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    return _draw(
        series.over_feature(view.coverage),
        f"{panels.title(view.coverage)}  -  coverage per observation",
        _FEATURE_GROUND,
        [],
        view.strategy.timeless,
    )


def plot_tile(chosen: TileView | None) -> widgets.Widget:
    """Draw the same panels for the tile on show.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when no tile is picked.
    """
    if chosen is None:
        return panels.unavailable(NO_TILE)
    return _draw(
        series.over_tile(chosen.track),
        f"{chosen.name}  -  coverage per observation",
        _TILE_GROUND,
        chosen.open_for,
        chosen.view.strategy.timeless,
    )


def _draw(
    drawn: Sequence[Series],
    title: str,
    ground: str,
    open_for: Sequence[Stretch],
    timeless: frozenset[str],
) -> widgets.Widget:
    """Draw one stacked panel per instrument set, sharing both axes.

    Args:
        drawn: What each set observed of the ground on show.
        title: The line above the top panel.
        ground: What the heights are a share of.
        open_for: The stretches of time the windows are open over.
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
    figure.supylabel(ground, fontsize=10)
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
    """Name the marked stretches of time, when the tiles earned any.

    Args:
        axis: The top panel, which carries the legend.
        open_for: The stretches of time the windows are open over.

    Returns:
        None.
    """
    if not open_for:
        return
    counted = (
        "the window the tile earned"
        if len(open_for) == 1
        else f"{len(open_for):,} stretches the tiles' windows open over"
    )
    marker = Line2D(
        [],
        [],
        color=panels.SURVEY_LINE,
        linestyle=panels.SURVEY_STYLE,
        linewidth=panels.SURVEY_WIDTH,
        label=counted,
    )
    axis.legend(handles=[marker], fontsize=8, loc="upper right", frameon=False)

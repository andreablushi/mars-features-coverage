"""What each single observation covered, at the time it was taken."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from models.results import SetCoverage
from visualization import configs, panels


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Draw one stacked panel per instrument set, sharing both axes.

    Args:
        coverage: The feature's instrument sets, widest coverage first.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    colours = panels.colours(coverage)
    area_km2 = coverage[0].summary.feature_area_km2
    figure, axes = plt.subplots(
        len(coverage),
        1,
        figsize=(configs.FIGURE_WIDTH, configs.PANEL_HEIGHT * len(coverage)),
        sharex=True,
        sharey=True,
    )
    axes = np.atleast_1d(axes)
    for axis, entry in zip(axes, coverage, strict=True):
        _panel(axis, entry, colours[entry.label], area_km2)
    axes[0].set_title(
        f"{panels.title(coverage)}  -  coverage per observation",
        fontsize=12,
        loc="left",
    )
    axes[-1].set_xlabel("Observation start time")
    figure.supylabel("Share of the feature covered by one observation", fontsize=10)
    figure.tight_layout()
    return panels.rendered(figure)


def _panel(axis, entry: SetCoverage, colour, area_km2: float) -> None:
    """Draw one instrument set's observations on its own panel.

    Args:
        axis: The panel to draw on.
        entry: The instrument set being drawn.
        colour: The colour the set is drawn in.
        area_km2: The feature's bounding box area, which the heights are a share of.

    Returns:
        None.
    """
    times = [event.t_start for event in entry.events]
    shares = [event.own_km2 / area_km2 for event in entry.events]
    axis.vlines(times, 0.0, shares, color=colour, alpha=0.35, linewidth=0.7)
    axis.scatter(
        times, shares, s=12, alpha=0.65, color=colour, edgecolors="none", zorder=3
    )
    if not entry.observed:
        axis.text(
            0.5,
            0.5,
            entry.reason,
            transform=axis.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            color=configs.GREY,
        )
    axis.set_ylabel(entry.label, rotation=0, ha="right", va="center", fontsize=9)
    axis.set_ylim(-0.05, 1.05)
    panels.tidy(axis, percent="y", grid="y")

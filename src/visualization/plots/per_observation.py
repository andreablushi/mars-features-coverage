"""What each single observation covered, at the time it was taken."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from models.results import SetCoverage
from visualization import configs, panels
from visualization.selectors.window import Window


def plot(coverage: Sequence[SetCoverage], window: Window) -> widgets.Widget:
    """Draw one stacked panel per instrument set, sharing the time axis.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range the panels are shown over, which the height
            scale is fitted to so zooming in on a quiet stretch opens it up.

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
    )
    axes = np.atleast_1d(axes)
    shared = _shared_top(coverage, area_km2, window)
    for axis, entry in zip(axes, coverage, strict=True):
        _panel(axis, entry, colours[entry.label], area_km2)
        top = 1.0 if _full_planet(entry) else shared
        axis.set_ylim(-0.05 * top, 1.05 * top)
    axes[0].set_xlim(left=window.start, right=window.end)
    axes[0].set_title(
        f"{panels.title(coverage)}  -  coverage per observation",
        fontsize=12,
        loc="left",
    )
    axes[-1].set_xlabel("Observation start time")
    figure.supylabel("Share of the feature covered by one observation", fontsize=10)
    figure.tight_layout()
    return panels.rendered(figure)


def _full_planet(entry: SetCoverage) -> bool:
    """Report whether a set covers the whole planet rather than a target.

    Args:
        entry: The instrument set being drawn.

    Returns:
        True when the set reaches every feature by construction, so its height
        says nothing about targeted observing and must not set the scale.
    """
    return entry.summary.iid in configs.FULL_PLANET_INSTRUMENTS


def _shared_top(
    coverage: Sequence[SetCoverage], area_km2: float, window: Window
) -> float:
    """Return the height the targeted panels are scaled to.

    A whole planet set sits at the full share of every feature, so leaving it
    in would pin the scale at 100% and flatten every targeted panel to a line
    along the axis. It is left out here and given its own scale instead.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        area_km2: The feature's bounding box area.
        window: The date range the panels are shown over.

    Returns:
        The tallest visible targeted observation as a share of the feature, or
        the full share when the window holds no targeted observation at all.
    """
    peak = max(
        (
            event.own_km2 / area_km2
            for entry in coverage
            if not _full_planet(entry)
            for event in window.visible(entry.events)
        ),
        default=0.0,
    )
    return peak if peak > 0.0 else 1.0


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
    panels.tidy(axis, percent="y", grid="y")

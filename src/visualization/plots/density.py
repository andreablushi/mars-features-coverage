"""When a feature's observations pile up, and which instruments overlap there."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.dates import date2num

from models.results import SetCoverage
from visualization import configs, panels
from visualization.selectors.window import Window, month_edges


def plot(coverage: Sequence[SetCoverage], window: Window) -> widgets.Widget:
    """Draw how many observations each instrument set took in each time bin.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range to bin over, one column per month of it.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    edges = _bins(coverage, window)
    counts = np.array([_counts(entry, window, edges) for entry in coverage])
    figure, axis = plt.subplots(
        figsize=(
            configs.FIGURE_WIDTH,
            configs.DENSITY_ROW_HEIGHT * len(coverage) + 1.8,
        )
    )
    colours = plt.get_cmap(configs.DENSITY_COLORMAP).with_extremes(
        bad=configs.DENSITY_EMPTY
    )
    mesh = axis.pcolormesh(
        date2num(edges),
        np.arange(len(coverage) + 1),
        np.ma.masked_equal(counts, 0),
        cmap=colours,
        norm=LogNorm(vmin=1, vmax=max(counts.max(), 2)),
    )
    _label(axis, coverage, edges)
    axis.set_title(
        f"{panels.title(coverage)}  -  observations per month",
        fontsize=12,
        loc="left",
    )
    axis.set_xlabel("Observation start time")
    bar = figure.colorbar(mesh, ax=axis, pad=0.01)
    bar.set_label("Observations in the month", fontsize=9)
    bar.ax.tick_params(labelsize=8)
    figure.tight_layout()
    return panels.rendered(figure)


def _bins(coverage: Sequence[SetCoverage], window: Window) -> list[datetime]:
    """Return one monthly bin edge per month the panel covers.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range to bin over, open at either end to take the
            record's own extent there.

    Returns:
        The edges in order, one more than there are months.
    """
    first = window.start or min(entry.summary.t_first for entry in coverage)
    last = window.end or max(entry.summary.t_last for entry in coverage)
    return month_edges(first, last)


def _counts(
    entry: SetCoverage, window: Window, edges: Sequence[datetime]
) -> np.ndarray:
    """Count one instrument set's observations in each time bin.

    Args:
        entry: The instrument set being counted.
        window: The date range, which excludes what falls outside it.
        edges: The bin edges, in order.

    Returns:
        One count per bin, in the same order.
    """
    times = [date2num(event.t_start) for event in window.visible(entry.events)]
    counts, _ = np.histogram(times, bins=date2num(edges))
    return counts


def _label(axis, coverage: Sequence[SetCoverage], edges: Sequence[datetime]) -> None:
    """Name each row after its instrument set, widest coverage on top.

    Args:
        axis: The panel to label.
        coverage: The feature's instrument sets, widest coverage first.
        edges: The bin edges, used to place the note on an empty row.

    Returns:
        None.
    """
    axis.set_yticks(np.arange(len(coverage)) + 0.5)
    axis.set_yticklabels([entry.label for entry in coverage], fontsize=9)
    for boundary in range(1, len(coverage)):
        axis.axhline(boundary, color=configs.DENSITY_ROW_EDGE, linewidth=0.6)
    axis.invert_yaxis()
    axis.xaxis_date()
    axis.tick_params(labelsize=8, length=0)
    axis.spines[:].set_visible(False)
    middle = (date2num(edges[0]) + date2num(edges[-1])) / 2
    for row, entry in enumerate(coverage):
        if not entry.observed:
            axis.text(
                middle,
                row + 0.5,
                entry.reason,
                ha="center",
                va="center",
                fontsize=8,
                color=configs.GREY,
            )

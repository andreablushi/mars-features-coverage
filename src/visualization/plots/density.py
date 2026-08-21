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
from visualization import panels
from visualization.selectors.window import Window, month_edges

# How many months one density column covers, however long the range is.
DENSITY_BIN_MONTHS = 1
DENSITY_ROW_HEIGHT = 0.5
DENSITY_EMPTY = "#ffffff"
DENSITY_ROW_EDGE = "#cccccc"


def plot(coverage: Sequence[SetCoverage], window: Window) -> widgets.Widget:
    """Draw how many observations each instrument set took in each time bin.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range to bin over, one column per bin of it.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    edges = date2num(_bins(coverage, window))
    counts = np.array([_counts(entry, window, edges) for entry in coverage])
    binned = _bin_name()
    figure, axis = plt.subplots(
        figsize=(
            panels.FIGURE_WIDTH,
            DENSITY_ROW_HEIGHT * len(coverage) + 1.8,
        )
    )
    colours = plt.get_cmap(panels.COLORMAP).with_extremes(bad=DENSITY_EMPTY)
    mesh = axis.pcolormesh(
        edges,
        np.arange(len(coverage) + 1),
        np.ma.masked_equal(counts, 0),
        cmap=colours,
        norm=LogNorm(vmin=1, vmax=max(counts.max(), 2)),
    )
    _label(axis, coverage, edges)
    axis.set_title(
        f"{panels.title(coverage)}  -  observations per {binned}",
        fontsize=12,
        loc="left",
    )
    axis.set_xlabel("Observation start time")
    bar = figure.colorbar(mesh, ax=axis, pad=0.01)
    bar.set_label(f"Observations in the {binned}", fontsize=9)
    bar.ax.tick_params(labelsize=8)
    figure.tight_layout()
    return panels.rendered(figure)


def _bin_name() -> str:
    """Name the configured bin width, for the title and the colour bar.

    Returns:
        The bin width as it reads in a sentence, such as "month" or
        "3 months".
    """
    months = DENSITY_BIN_MONTHS
    return "month" if months == 1 else f"{months} months"


def _bins(coverage: Sequence[SetCoverage], window: Window) -> list[datetime]:
    """Return the bin edges the panel covers, at the configured width.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range to bin over, open at either end to take the
            record's own extent there.

    Returns:
        The edges in order, one more than there are bins.
    """
    first = window.start or min(entry.summary.t_first for entry in coverage)
    last = window.end or max(entry.summary.t_last for entry in coverage)
    return month_edges(first, last, DENSITY_BIN_MONTHS)


def _counts(entry: SetCoverage, window: Window, edges: np.ndarray) -> np.ndarray:
    """Count one instrument set's observations in each time bin.

    Args:
        entry: The instrument set being counted.
        window: The date range, which excludes what falls outside it.
        edges: The bin edges as matplotlib date numbers, in order.

    Returns:
        One count per bin, in the same order.
    """
    times = [date2num(event.t_start) for event in window.visible(entry.events)]
    counts, _ = np.histogram(times, bins=edges)
    return counts


def _label(axis, coverage: Sequence[SetCoverage], edges: np.ndarray) -> None:
    """Name each row after its instrument set, widest coverage on top.

    Args:
        axis: The panel to label.
        coverage: The feature's instrument sets, widest coverage first.
        edges: The bin edges as date numbers, placing the note on an empty row.

    Returns:
        None.
    """
    axis.set_yticks(np.arange(len(coverage)) + 0.5)
    axis.set_yticklabels([entry.label for entry in coverage], fontsize=9)
    for boundary in range(1, len(coverage)):
        axis.axhline(boundary, color=DENSITY_ROW_EDGE, linewidth=0.6)
    axis.invert_yaxis()
    axis.xaxis_date()
    axis.tick_params(labelsize=8, length=0)
    axis.spines[:].set_visible(False)
    for row, entry in enumerate(coverage):
        if not entry.observed:
            axis.text(
                (edges[0] + edges[-1]) / 2,
                row + 0.5,
                entry.reason,
                ha="center",
                va="center",
                fontsize=8,
                color=panels.GREY,
            )

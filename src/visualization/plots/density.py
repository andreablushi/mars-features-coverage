"""When a feature's observations pile up, and which instruments overlap there."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.dates import date2num

from models.results import SetCoverage
from visualization import panels

# How many months one density column covers, however long the range is.
DENSITY_BIN_MONTHS = 1
DENSITY_ROW_HEIGHT = 0.5
DENSITY_EMPTY = "#ffffff"
DENSITY_ROW_EDGE = "#cccccc"


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Draw how many observations each instrument set took in each time bin.

    Args:
        coverage: The feature's instrument sets, widest coverage first.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    edges = date2num(_bins(coverage))
    counts = np.array([_counts(instrument, edges) for instrument in coverage])
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


def _bins(coverage: Sequence[SetCoverage]) -> list[datetime]:
    """Return the bin edges the panel covers, at the configured width.

    Args:
        coverage: The feature's instrument sets, widest coverage first.

    Returns:
        The edges in order, one more than there are bins.
    """
    first = min(instrument.summary.t_first for instrument in coverage)
    last = max(instrument.summary.t_last for instrument in coverage)
    return _month_edges(first, last, DENSITY_BIN_MONTHS)


def _month_edges(first: datetime, last: datetime, step: int) -> list[datetime]:
    """Return bin edges every step months, covering a period whole.

    The last edge always sits past the end of the period, so the final bin is
    closed and the month holding last is counted in it.

    Args:
        first: The earliest moment the bins must cover.
        last: The latest moment they must cover.
        step: How many months one bin spans.

    Returns:
        The edges in UTC, in order, one more than there are bins.
    """
    cursor, stop = _first_of(first), _first_of(last)
    edges = []
    while cursor <= stop:
        edges.append(datetime.combine(cursor, time.min, UTC))
        for _ in range(step):
            cursor = _first_of_next(cursor)
    edges.append(datetime.combine(cursor, time.min, UTC))
    return edges


def _first_of(moment: datetime) -> date:
    """Return the first day of a moment's own month.

    Args:
        moment: The moment to place.

    Returns:
        The first day of the month it falls in.
    """
    return date(moment.year, moment.month, 1)


def _first_of_next(day: date) -> date:
    """Return the first day of the month after a day's own.

    Args:
        day: The day to step on from.

    Returns:
        The first day of the following month.
    """
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def _counts(instrument: SetCoverage, edges: np.ndarray) -> np.ndarray:
    """Count one instrument set's observations in each time bin.

    Args:
        instrument: The instrument set being counted.
        edges: The bin edges as matplotlib date numbers, in order.

    Returns:
        One count per bin, in the same order.
    """
    times = [date2num(observation.t_start) for observation in instrument.events]
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
    axis.set_yticklabels([instrument.label for instrument in coverage], fontsize=9)
    for boundary in range(1, len(coverage)):
        axis.axhline(boundary, color=DENSITY_ROW_EDGE, linewidth=0.6)
    axis.invert_yaxis()
    axis.xaxis_date()
    axis.tick_params(labelsize=8, length=0)
    axis.spines[:].set_visible(False)
    for row, instrument in enumerate(coverage):
        if not instrument.observed:
            axis.text(
                (edges[0] + edges[-1]) / 2,
                row + 0.5,
                instrument.reason,
                ha="center",
                va="center",
                fontsize=8,
                color=panels.GREY,
            )

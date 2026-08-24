"""When the observations pile up, and which instruments overlap there."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.dates import date2num

from visualization.common import panels, series
from visualization.common.picker import View
from visualization.common.series import Series
from visualization.feature.picker import NO_TILE, TileView

# How many months one density column covers, however long the range is.
DENSITY_BIN_MONTHS = 1
DENSITY_ROW_HEIGHT = 0.5
DENSITY_EMPTY = "#ffffff"
DENSITY_ROW_EDGE = "#cccccc"


def plot(view: View) -> widgets.Widget:
    """Draw how many observations each set took of the feature per time bin.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    return _draw(series.over_feature(view.coverage), panels.title(view.coverage))


def plot_tile(chosen: TileView | None) -> widgets.Widget:
    """Draw the same rows for the tile on show.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when no tile is picked.
    """
    if chosen is None:
        return panels.unavailable(NO_TILE)
    return _draw(series.over_tile(chosen.track), chosen.name)


def _draw(drawn: Sequence[Series], title: str) -> widgets.Widget:
    """Draw one row per instrument set, coloured by how busy each bin was.

    Args:
        drawn: What each set observed of the ground on show.
        title: The line above the panel.

    Returns:
        The figure as a widget.
    """
    edges = date2num(_bins(drawn))
    counts = np.array([_counts(one, edges) for one in drawn])
    binned = _bin_name()
    figure, axis = plt.subplots(
        figsize=(panels.FIGURE_WIDTH, DENSITY_ROW_HEIGHT * len(drawn) + 1.8)
    )
    colours = plt.get_cmap(panels.COLORMAP).with_extremes(bad=DENSITY_EMPTY)
    mesh = axis.pcolormesh(
        edges,
        np.arange(len(drawn) + 1),
        np.ma.masked_equal(counts, 0),
        cmap=colours,
        norm=LogNorm(vmin=1, vmax=max(counts.max(), 2)),
    )
    _label(axis, drawn, edges)
    axis.set_title(f"{title}  -  observations per {binned}", fontsize=12, loc="left")
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


def _bins(drawn: Sequence[Series]) -> list[datetime]:
    """Return the bin edges the panel covers, at the configured width.

    Args:
        drawn: What each set observed of the ground on show.

    Returns:
        The edges in order, one more than there are bins.
    """
    first = min(one.first for one in drawn)
    last = max(one.last for one in drawn)
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


def _counts(one: Series, edges: np.ndarray) -> np.ndarray:
    """Count one instrument set's observations in each time bin.

    Args:
        one: What the set observed.
        edges: The bin edges as matplotlib date numbers, in order.

    Returns:
        One count per bin, in the same order.
    """
    counts, _ = np.histogram([date2num(moment) for moment in one.times], bins=edges)
    return counts


def _label(axis, drawn: Sequence[Series], edges: np.ndarray) -> None:
    """Name each row after its instrument set, widest coverage on top.

    Args:
        axis: The panel to label.
        drawn: What each set observed of the ground on show.
        edges: The bin edges as date numbers, placing the note on an empty row.

    Returns:
        None.
    """
    axis.set_yticks(np.arange(len(drawn)) + 0.5)
    axis.set_yticklabels([one.label for one in drawn], fontsize=9)
    for boundary in range(1, len(drawn)):
        axis.axhline(boundary, color=DENSITY_ROW_EDGE, linewidth=0.6)
    axis.invert_yaxis()
    axis.xaxis_date()
    axis.tick_params(labelsize=8, length=0)
    axis.spines[:].set_visible(False)
    for row, one in enumerate(drawn):
        if not one.observed:
            axis.text(
                (edges[0] + edges[-1]) / 2,
                row + 0.5,
                one.reason,
                ha="center",
                va="center",
                fontsize=8,
                color=panels.GREY,
            )

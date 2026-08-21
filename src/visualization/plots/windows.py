"""Which stretch of time a feature's observations can be clustered into."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import PowerNorm
from matplotlib.dates import date2num
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from campaign.results import Campaign
from models.results import SetCoverage
from visualization import campaigns, candidates, configs, panels
from visualization.candidates import Grid
from visualization.selectors.window import Window

_TOO_SHORT = "This feature's record is too short to hold a choice of windows."
_UNSOUNDED = "no sounder track in the window"
_SILENT = "no sounder reached this feature at all"
_INSTRUMENTS = "{count} instruments in the window"
_PICK = {
    "marker": "o",
    "linestyle": "none",
    "color": configs.WINDOW_PICKED,
    "markersize": configs.WINDOW_PICKED_SIZE,
    "markeredgecolor": configs.WINDOW_PICKED_EDGE,
    "markeredgewidth": 1.0,
    "zorder": 5,
}


def plot(coverage: Sequence[SetCoverage], window: Window) -> widgets.Widget:
    """Draw every window the feature could be clustered into, and what it reaches.

    Args:
        coverage: The feature's instrument sets, in the order the config names them.
        window: The date range to look for windows inside.

    Returns:
        The figure as a widget, or the grey panel when there is nothing to
        choose between.
    """
    if not coverage:
        return panels.unavailable()
    grid = candidates.build(coverage, window)
    if grid is None:
        return panels.unavailable(_TOO_SHORT)
    figure, axis = plt.subplots(figsize=configs.WINDOW_FIGURE_SIZE)
    mesh = _field(axis, grid, campaigns.picked(coverage, window))
    axis.set_title(
        f"{panels.title(coverage)}  -  candidate time windows", fontsize=12, loc="left"
    )
    axis.set_xlim(grid.centres[0], grid.centres[-1])
    bar = figure.colorbar(mesh, ax=axis, pad=0.01)
    bar.set_label(
        "Share of the feature reached, counted evenly over instruments", fontsize=9
    )
    bar.ax.tick_params(labelsize=8)
    figure.tight_layout()
    return panels.rendered(figure)


def _field(axis: Axes, grid: Grid, picked: Campaign | None):
    """Draw what every candidate window reaches, by when it opens and how long.

    Args:
        axis: The panel to draw on.
        grid: The scored candidate windows.
        picked: The window the search chose, or None when it found none.

    Returns:
        The mesh, for the colour bar to read its colours from.
    """
    colours = plt.get_cmap(configs.DENSITY_COLORMAP).with_extremes(
        bad=configs.WINDOW_UNSOUNDED
    )
    mesh = axis.pcolormesh(
        _steps(grid.centres),
        _steps(grid.widths, log=True),
        _held(grid),
        cmap=colours,
        norm=PowerNorm(configs.WINDOW_GAMMA, vmin=0.0, vmax=1.0),
    )
    _contours(axis, grid)
    _silent(axis, grid)
    _marked(axis, grid, picked)
    axis.legend(
        handles=_keys(grid, picked),
        fontsize=8,
        loc="lower right",
        framealpha=0.85,
        edgecolor="none",
    )
    axis.set_yscale("log")
    axis.xaxis_date()
    axis.set_xlabel("What the window is centred on")
    axis.set_ylabel("How long the window lasts")
    _ladder(axis, grid.widths)
    axis.tick_params(labelsize=8)
    return mesh


def _contours(axis: Axes, grid: Grid) -> None:
    """Ring the windows holding two instruments, then three, and so on.

    Args:
        axis: The panel to draw on.
        grid: The scored candidate windows.

    Returns:
        None.
    """
    rings = _rings(grid)
    if not rings:
        return
    axis.contour(
        grid.centres,
        grid.widths,
        grid.instruments,
        levels=[count - 0.5 for count, _, _ in rings],
        colors=configs.WINDOW_CONTOUR,
        linestyles=[style for _, style, _ in rings],
        linewidths=[width for _, _, width in rings],
    )


def _rings(grid: Grid) -> list[tuple[int, str, float]]:
    """Decide which instrument counts to ring, and how to draw each ring.

    Args:
        grid: The scored candidate windows.

    Returns:
        The count, the line style, and the line width of every ring, the one
        holding every instrument last and drawn solid.
    """
    most = int(grid.instruments.max())
    return [
        (
            count,
            "solid" if count == most else "dotted",
            configs.WINDOW_RING_ALL if count == most else configs.WINDOW_RING,
        )
        for count in range(2, most + 1)
    ]


def _marked(axis: Axes, grid: Grid, picked: Campaign | None) -> None:
    """Mark the window the search picked on the grid it was chosen from.

    Args:
        axis: The panel to draw on.
        grid: The scored candidate windows.
        picked: The window the search chose, or None when it found none.

    Returns:
        None.
    """
    if picked is None:
        return
    centre, length = _at(grid, picked)
    axis.plot([centre], [length], **_PICK)


def _at(grid: Grid, picked: Campaign) -> tuple[float, float]:
    """Place the chosen window on the two axes the candidates are drawn on.

    A window shorter than the shortest length drawn is marked on the bottom
    row, which is as close to it as the panel reaches.

    Args:
        grid: The scored candidate windows.
        picked: The window the search chose.

    Returns:
        What it is centred on, as a date number, and how long it lasts in days.
    """
    opened, closed = date2num(picked.start), date2num(picked.end)
    return (opened + closed) / 2.0, max(closed - opened, float(grid.widths[0]))


def _keys(grid: Grid, picked: Campaign | None) -> list:
    """Name every ring the panel draws, the window it marks, and the grey it leaves.

    Args:
        grid: The scored candidate windows.
        picked: The window the search chose, or None when it found none.

    Returns:
        The legend handles, in the order they read.
    """
    rings = [
        Line2D(
            [],
            [],
            color=configs.WINDOW_CONTOUR,
            linestyle=style,
            linewidth=width,
            label=_INSTRUMENTS.format(count=count),
        )
        for count, style, width in _rings(grid)
    ]
    grey = Patch(facecolor=configs.WINDOW_UNSOUNDED, label=_UNSOUNDED)
    if picked is None:
        return rings + [grey]
    return [Line2D([], [], label=picked.caption, **_PICK)] + rings + [grey]


def _held(grid: Grid) -> np.ma.MaskedArray:
    """Hide the windows no sounder track passes through.

    Args:
        grid: The scored candidate windows.

    Returns:
        The coverage, masked where a window holds no track.
    """
    return np.ma.masked_where(~grid.sounded, grid.reached)


def _silent(axis: Axes, grid: Grid) -> None:
    """Say so on the panel when no window anywhere holds a sounder track.

    Args:
        axis: The panel to draw on.
        grid: The scored candidate windows.

    Returns:
        None.
    """
    if grid.sounded.any():
        return
    axis.text(
        0.5,
        0.5,
        _SILENT,
        transform=axis.transAxes,
        ha="center",
        va="center",
        fontsize=10,
        color=configs.GREY,
    )


def _ladder(axis: Axes, widths: np.ndarray) -> None:
    """Label the window lengths in months and years rather than in days.

    Args:
        axis: The panel carrying the lengths.
        widths: The lengths drawn, in days, shortest first.

    Returns:
        None.
    """
    marks = [
        (days, name)
        for days, name in configs.WINDOW_TICKS
        if widths[0] <= days <= widths[-1]
    ]
    axis.set_yticks([days for days, _ in marks], [name for _, name in marks])
    axis.set_yticks([], minor=True)


def _steps(points: np.ndarray, log: bool = False) -> np.ndarray:
    """Return the cell edges around evenly spaced sample points.

    Args:
        points: The sample points, evenly spaced on their own scale.
        log: Whether they are spaced evenly in the logarithm rather than
            in the value.

    Returns:
        The edges, one more than there are points.
    """
    scaled = np.log(points) if log else points
    step = scaled[1] - scaled[0]
    edges = np.concatenate([scaled - step / 2.0, [scaled[-1] + step / 2.0]])
    return np.exp(edges) if log else edges

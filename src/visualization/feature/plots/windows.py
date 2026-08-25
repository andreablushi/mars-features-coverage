"""Which stretch of time a tile's observations can be clustered into."""

from __future__ import annotations

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import PowerNorm
from matplotlib.dates import date2num
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from survey.models.survey import Survey
from utils.maths import quantities
from visualization.common import panels
from visualization.feature.picker import NO_TILE, TileView
from visualization.feature.stats import candidates
from visualization.feature.stats.candidates import Grid

# How large the grid of candidates is drawn.
WINDOW_FIGURE_SIZE = (12, 6)

# How a window holding no sounder track is drawn, and how the counts are traced.
WINDOW_UNSOUNDED = "#d9d9d9"
WINDOW_CONTOUR = "#4d4d4d"

# The window the search picked, marked on the grid of candidates it was chosen from.
WINDOW_PICKED = "#d62728"
WINDOW_PICKED_EDGE = "#ffffff"
WINDOW_PICKED_SIZE = 6.0

# How hard the colours lean towards the low shares a short window reaches.
WINDOW_GAMMA = 0.5

# How the instrument count rings are drawn, the ring holding every one of them last.
WINDOW_RING = 0.7
WINDOW_RING_ALL = 1.5
WINDOW_TICKS = [
    (1.0, "1 day"),
    (7.0, "1 week"),
    (30.0, "1 month"),
    (91.0, "3 months"),
    (183.0, "6 months"),
    (365.0, "1 year"),
    (687.0, "1 Mars year"),
    (730.0, "2 years"),
    (1826.0, "5 years"),
    (3652.0, "10 years"),
    (7305.0, "20 years"),
]

_TOO_SHORT = "This tile's record is too short to hold a choice of windows."
_UNSOUNDED = "no sounder track in the window"
_SILENT = "no sounder reached this tile at all"
_INSTRUMENTS = "{count} instruments in the window"
_PICK = {
    "marker": "o",
    "linestyle": "none",
    "color": WINDOW_PICKED,
    "markersize": WINDOW_PICKED_SIZE,
    "markeredgecolor": WINDOW_PICKED_EDGE,
    "markeredgewidth": 1.0,
    "zorder": 5,
}


def plot(chosen: TileView | None) -> widgets.Widget:
    """Draw every window the tile could be clustered into, and what it reaches.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when there is nothing to
        choose between.
    """
    if chosen is None:
        return panels.unavailable(NO_TILE)
    grid = candidates.build(chosen.track, chosen.view.strategy)
    if grid is None:
        return panels.unavailable(_TOO_SHORT)
    figure, axis = panels.board(WINDOW_FIGURE_SIZE)
    mesh = _field(axis, grid, chosen.survey, _instruments(chosen))
    axis.set_title(f"{chosen.name}  -  candidate time windows", fontsize=12, loc="left")
    axis.set_xlim(grid.centres[0], grid.centres[-1])
    bar = figure.colorbar(mesh, ax=axis, pad=0.01)
    bar.set_label(
        "Share of the tile reached, counted evenly over instruments", fontsize=9
    )
    bar.ax.tick_params(labelsize=8)
    figure.tight_layout()
    return panels.rendered(figure)


def _instruments(chosen: TileView) -> int:
    """Count the instruments the window the search picked holds.

    Args:
        chosen: The tile on show.

    Returns:
        How many instruments left an observation inside it, and nought when
        the tile earned no window.
    """
    if chosen.survey is None:
        return 0
    track = chosen.track
    return len({track.iids[track.owners[index]] for index in chosen.survey.kept})


def _field(axis: Axes, grid: Grid, picked: Survey | None, holds: int):
    """Draw what every candidate window reaches, by when it opens and how long.

    Args:
        axis: The panel to draw on.
        grid: The scored candidate windows.
        picked: The window the search chose, or None when it found none.
        holds: How many instruments that window holds.

    Returns:
        The mesh, for the colour bar to read its colours from.
    """
    colours = plt.get_cmap(panels.COLORMAP).with_extremes(bad=WINDOW_UNSOUNDED)
    mesh = axis.pcolormesh(
        _steps(grid.centres),
        _steps(grid.widths, log=True),
        _held(grid),
        cmap=colours,
        norm=PowerNorm(WINDOW_GAMMA, vmin=0.0, vmax=1.0),
    )
    _contours(axis, grid)
    _silent(axis, grid)
    _marked(axis, grid, picked)
    axis.legend(
        handles=_keys(grid, picked, holds),
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
        colors=WINDOW_CONTOUR,
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
            "solid" if count == most else "dashed",
            WINDOW_RING_ALL if count == most else WINDOW_RING,
        )
        for count in range(2, most + 1)
    ]


def _marked(axis: Axes, grid: Grid, picked: Survey | None) -> None:
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
    opened, closed = date2num(picked.start), date2num(picked.end)
    axis.plot(
        [(opened + closed) / 2.0],
        [max(closed - opened, float(grid.widths[0]))],
        **_PICK,
    )


def _keys(grid: Grid, picked: Survey | None, holds: int) -> list:
    """Name every ring the panel draws, the window it marks, and the grey it leaves.

    Args:
        grid: The scored candidate windows.
        picked: The window the search chose, or None when it found none.
        holds: How many instruments that window holds.

    Returns:
        The legend handles, in the order they read.
    """
    rings = [
        Line2D(
            [],
            [],
            color=WINDOW_CONTOUR,
            linestyle=style,
            linewidth=width,
            label=_INSTRUMENTS.format(count=count),
        )
        for count, style, width in _rings(grid)
    ]
    grey = Patch(facecolor=WINDOW_UNSOUNDED, label=_UNSOUNDED)
    if picked is None:
        return rings + [grey]
    label = (
        f"best window: {quantities.duration(picked.days)}, "
        f"{holds} instruments, scoring {picked.reach:.0%}"
    )
    return [Line2D([], [], label=label, **_PICK)] + rings + [grey]


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
        color=panels.GREY,
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
        (days, name) for days, name in WINDOW_TICKS if widths[0] <= days <= widths[-1]
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

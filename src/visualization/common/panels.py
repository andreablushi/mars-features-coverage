"""How a figure reads: its colours, its axes, and what stands in for it."""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import datetime
from html import escape
from itertools import cycle

import ipywidgets as widgets
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter

from models.results import SetCoverage
from visualization.common.series import Series

GREY = "#8a8a8a"

# How wide every stacked figure is drawn.
FIGURE_WIDTH = 11

# The ramp a heat panel is coloured by.
COLORMAP = "YlGnBu"

# The strip left clear under a map for the key naming what it draws.
KEY_HEIGHT = 0.085
KEY_DROP = 0.015

# The strip left clear beside a map for the same key, set down its side.
KEY_WIDTH = 0.78
KEY_SIDE = 0.80
KEY_TOP = 0.92

# The windows the tiles earned, marked across the time panels.
SURVEY_LINE = "#1a1a1a"
SURVEY_STYLE = (0, (6, 3))
SURVEY_WIDTH = 0.8
SURVEY_SHADE = "#9e9e9e"
SURVEY_ALPHA = 0.18


Colour = tuple[float, float, float]


def colours(drawn: Sequence[Series]) -> dict[str, Colour]:
    """Assign a colour to each instrument set.

    Args:
        drawn: What each set observed, in the order to colour them.

    Returns:
        One colour per instrument set label.
    """
    wheel = cycle(plt.cm.tab10.colors)
    return {one.label: colour for one, colour in zip(drawn, wheel, strict=False)}


def board(size: tuple[float, float]) -> tuple[Figure, Axes]:
    """Open a figure off pyplot's registry, so a thread may draw on it.

    A figure pyplot owns is shown and closed by the notebook at the end of
    whichever cell happens to run next, which is not the cell that asked for
    it when the drawing is done off the main thread.

    Args:
        size: How wide and tall to draw it, in inches.

    Returns:
        The figure and the single panel on it.
    """
    figure = Figure(figsize=size)
    return figure, figure.subplots()


def key_below(figure: Figure, handles: Sequence) -> None:
    """Set a key under a map, in a strip left clear of the axis and its label.

    Args:
        figure: The finished figure, whose panel is laid out above the strip.
        handles: What the key names, in the order it reads.

    Returns:
        None.
    """
    figure.tight_layout(rect=(0.0, KEY_HEIGHT, 1.0, 1.0))
    figure.legend(
        handles=handles,
        fontsize=8,
        loc="lower left",
        bbox_to_anchor=(0.02, KEY_DROP),
        ncols=3,
        frameon=False,
    )


def key_beside(figure: Figure, handles: Sequence) -> None:
    """Set a key beside a map, in a strip left clear down its right side.

    Args:
        figure: The finished figure, whose panel is laid out left of the
            strip.
        handles: What the key names, in the order it reads.

    Returns:
        None.
    """
    figure.tight_layout(rect=(0.0, 0.0, KEY_WIDTH, 1.0))
    figure.legend(
        handles=handles,
        fontsize=8,
        loc="upper left",
        bbox_to_anchor=(KEY_SIDE, KEY_TOP),
        frameon=False,
    )


def tidy(axis: Axes, percent: str, grid: str) -> None:
    """Format an axis as percentages, grid it faintly, and drop its outer frame.

    Args:
        axis: The axis to style.
        percent: Which axis carries the coverage share, "x" or "y".
        grid: Which axis to draw gridlines along, "x", "y", or "both".

    Returns:
        None.
    """
    formatter = PercentFormatter(xmax=1.0, decimals=0)
    target = axis.xaxis if percent == "x" else axis.yaxis
    target.set_major_formatter(formatter)
    axis.grid(axis=grid, alpha=0.25, linewidth=0.5)
    axis.spines[["top", "right"]].set_visible(False)


def shade(axis: Axes, open_for: Sequence[tuple[datetime, datetime]]) -> None:
    """Mark the stretches of time the tiles' windows are open over.

    Args:
        axis: The panel to draw on, whose x axis carries time.
        open_for: When each stretch opens and closes, earliest first.

    Returns:
        None.
    """
    for opened, closed in open_for:
        axis.axvspan(opened, closed, color=SURVEY_SHADE, alpha=SURVEY_ALPHA, zorder=0)
        for edge in (opened, closed):
            axis.axvline(
                edge,
                color=SURVEY_LINE,
                linestyle=SURVEY_STYLE,
                linewidth=SURVEY_WIDTH,
                zorder=4,
            )


def rendered(figure: Figure) -> widgets.Image:
    """Turn a finished figure into a widget and release the figure.

    Args:
        figure: The finished figure, which is closed here.

    Returns:
        The figure as an image widget that can replace an earlier one.
    """
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=figure.dpi)
    if figure.canvas.manager is not None:
        plt.close(figure)
    return widgets.Image(
        value=buffer.getvalue(),
        format="png",
        layout=widgets.Layout(max_width="100%", height="auto"),
    )


def unavailable(
    message: str = "Confirm a feature with local data above to fill this in.",
) -> widgets.HTML:
    """Build the grey panel shown when there is nothing to draw.

    Args:
        message: The line explaining what is missing.

    Returns:
        The rendered panel.
    """
    return widgets.HTML(
        f"""<div style="
            background: repeating-linear-gradient(45deg,
                #ebebeb, #ebebeb 10px, #e0e0e0 10px, #e0e0e0 20px);
            border: 1px solid #c4c4c4; border-radius: 6px; color: {GREY};
            font-family: sans-serif; padding: 28px; text-align: center;">
          <div style="font-size: 15px; font-weight: 600;">No local data</div>
          <div style="font-size: 13px; margin-top: 6px;">{escape(message)}</div>
        </div>"""
    )


def title(coverage: Sequence[SetCoverage]) -> str:
    """Return the feature a loaded coverage belongs to.

    Args:
        coverage: The feature's instrument sets, which all carry its name.

    Returns:
        The feature class and name, such as "Crater / Jezero".
    """
    summary = coverage[0].summary
    return f"{summary.feature_class} / {summary.feature_name}"

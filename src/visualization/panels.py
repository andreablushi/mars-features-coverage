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
from survey.models.survey import Survey
from utils.maths import quantities

GREY = "#8a8a8a"

# How wide every stacked figure is drawn.
FIGURE_WIDTH = 11

# The ramp a heat panel is coloured by.
COLORMAP = "YlGnBu"

# The window the search picked, marked at either end of the time panels.
SURVEY_LINE = "#1a1a1a"
SURVEY_STYLE = (0, (6, 3))
SURVEY_WIDTH = 0.8


Colour = tuple[float, float, float]


def colours(coverage: Sequence[SetCoverage]) -> dict[str, Colour]:
    """Assign a colour to each instrument set.

    Args:
        coverage: The feature's instrument sets, in the order to colour them.

    Returns:
        One colour per instrument set label.
    """
    wheel = cycle(plt.cm.tab10.colors)
    return {
        instrument.label: colour
        for instrument, colour in zip(coverage, wheel, strict=False)
    }


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


def bracket(axis: Axes, start: datetime, end: datetime) -> None:
    """Mark a stretch of time on a panel with a line at either end of it.

    Args:
        axis: The panel to draw on, whose x axis carries time.
        start: When the stretch opens.
        end: When it closes.

    Returns:
        None.
    """
    for edge in (start, end):
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


def caption(survey: Survey) -> str:
    """Sum the picked window up in one line, for a legend or a title.

    Args:
        survey: The window the search picked.

    Returns:
        Its length, how many instruments it holds, and what it scores.
    """
    return (
        f"best window: {quantities.duration(survey.days)}, "
        f"{survey.instruments} instruments, scoring {survey.reach:.0%}"
    )

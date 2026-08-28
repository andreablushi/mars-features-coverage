"""How many pixels one observation lands, instrument by instrument."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

from utils.maths import quantities
from visualization.common import panels, series, wording
from visualization.common.picker import View
from visualization.common.series import Series
from visualization.feature.picker import NO_TILE, TileView

# One panel per instrument set, each on a scale of its own, so height is per panel
PANEL_HEIGHT = 1.55

# The strips left clear above and below the panels, in inches, for the line
# naming the ground and the line saying the panels share no scale.
TITLE_BAND = 0.42
NOTE_BAND = 0.58

# How many bars one panel's distribution is drawn in.
BARS = 26

# How the middle of a panel's distribution is marked.
MIDDLE_COLOUR = "#1a1a1a"
MIDDLE_STYLE = (0, (4, 2))
MIDDLE_WIDTH = 1.0

# How far apart a panel's bars are set when every observation landed the same count.
FLAT_DECADE = 1.2

# Where a panel is labelled between the decades, so a narrow one still reads,
# and the most decades it may span before those labels start running together.
BETWEEN_DECADES = (2.0, 5.0)
CROWDED_DECADES = 3.0

_TRACES = "traces"
_PIXELS = "px"
_NOTHING = "no pixel count"
_FEATURE_LANDED = "Pixels one observation lands on the feature"
_TILE_LANDED = "Pixels one observation lands on the tile"
_NOTE = (
    "Each panel carries a log scale of its own, since the instruments land counts "
    "orders of magnitude apart, and its dashed line\n"
    "marks its own middle observation. Read a shape against its panel alone: a bar "
    "here is never as wide as a bar there."
)


def plot(view: View) -> widgets.Widget:
    """Draw what one observation of each instrument lands on the whole feature.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    return _draw(
        series.over_feature(view.coverage),
        f"{panels.title(view.coverage)}  -  pixels per observation",
        _FEATURE_LANDED,
    )


def plot_tile(chosen: TileView | None) -> widgets.Widget:
    """Draw the same panels for the tile on show.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when no tile is picked.
    """
    if chosen is None:
        return panels.unavailable(NO_TILE)
    return _draw(
        series.over_tile(chosen.track),
        f"{chosen.name}  -  pixels per observation",
        _TILE_LANDED,
    )


def _draw(drawn: Sequence[Series], title: str, landed: str) -> widgets.Widget:
    """Draw one panel per instrument set, none of them sharing a scale.

    Args:
        drawn: What each set observed of the ground on show.
        title: The line above the top panel.
        landed: What the counts are counted over.

    Returns:
        The figure as a widget.
    """
    colours = panels.colours(drawn)
    tall = PANEL_HEIGHT * len(drawn) + TITLE_BAND + NOTE_BAND
    figure, axes = plt.subplots(len(drawn), 1, figsize=(panels.FIGURE_WIDTH, tall))
    axes = np.atleast_1d(axes)
    for axis, one in zip(axes, drawn, strict=True):
        _panel(axis, one, colours[one.label])
    axes[-1].set_xlabel(landed)
    figure.supylabel("Observations", fontsize=10)
    # Both strips are measured in inches, so they hold however many panels there are
    above, below = TITLE_BAND / tall, NOTE_BAND / tall
    figure.tight_layout(rect=(0.0, below, 1.0, 1.0 - above))
    figure.text(0.01, 1.0 - above / 2.0, title, fontsize=12, va="center")
    figure.text(0.01, below / 2.0, _NOTE, fontsize=8, color=panels.GREY, va="center")
    return panels.rendered(figure)


def _panel(axis: Axes, one: Series, colour) -> None:
    """Draw one instrument set's counts on a log scale of its own.

    Args:
        axis: The panel to draw on.
        one: What the set observed.
        colour: The colour the set is drawn in.

    Returns:
        None.
    """
    landed = np.asarray([count for count in one.pixels if count > 0.0], dtype=float)
    if landed.size:
        axis.hist(landed, bins=_bars(landed), color=colour, alpha=0.75, linewidth=0)
        axis.set_xscale("log")
        _ticks(axis, landed)
        _middle(axis, landed)
        _reading(axis, one, landed)
    else:
        axis.text(
            0.5,
            0.5,
            one.reason or _NOTHING,
            transform=axis.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            color=panels.GREY,
        )
        axis.set_xticks([])
    axis.set_ylabel(one.label, rotation=0, ha="right", va="center", fontsize=9)
    axis.set_yticks([])
    axis.tick_params(labelsize=8)
    axis.grid(axis="x", alpha=0.25, linewidth=0.5)
    axis.spines[["top", "right", "left"]].set_visible(False)


def _bars(landed: np.ndarray) -> np.ndarray:
    """Space one panel's bars evenly along its own log scale.

    Args:
        landed: The counts the panel draws, every one of them above nought.

    Returns:
        The bar edges, held apart where every observation landed the same count.
    """
    low, high = float(landed.min()), float(landed.max())
    if low == high:
        low, high = low / FLAT_DECADE, high * FLAT_DECADE
    return np.logspace(np.log10(low), np.log10(high), BARS + 1)


def _ticks(axis: Axes, landed: np.ndarray) -> None:
    """Label a log scale by its decades, and between them where it runs narrow.

    Args:
        axis: The panel to label.
        landed: The counts it draws, whose span says how much room a label has.

    Returns:
        None.
    """
    spans = np.log10(float(landed.max()) / float(landed.min()) or 1.0)
    axis.xaxis.set_minor_locator(LogLocator(subs=BETWEEN_DECADES))
    axis.xaxis.set_major_formatter(FuncFormatter(_short))
    axis.xaxis.set_minor_formatter(
        NullFormatter() if spans > CROWDED_DECADES else FuncFormatter(_short)
    )


def _middle(axis: Axes, landed: np.ndarray) -> None:
    """Mark where the middle observation of a panel falls.

    Args:
        axis: The panel to draw on.
        landed: The counts it draws.

    Returns:
        None.
    """
    axis.axvline(
        float(np.median(landed)),
        color=MIDDLE_COLOUR,
        linestyle=MIDDLE_STYLE,
        linewidth=MIDDLE_WIDTH,
        zorder=3,
    )


def _reading(axis: Axes, one: Series, landed: np.ndarray) -> None:
    """Say what the panel adds up to, in the units the instrument counts in.

    Args:
        axis: The panel to write on.
        one: The instrument set the panel draws.
        landed: The counts it draws.

    Returns:
        None.
    """
    unit = _TRACES if one.iid == wording.SOUNDER else _PIXELS
    axis.set_title(
        f"{landed.size:,} observations  -  "
        f"middle one lands {quantities.compact(float(np.median(landed)))} {unit}  -  "
        f"{quantities.compact(float(landed.sum()))} {unit} in all",
        fontsize=8,
        color=panels.GREY,
        loc="left",
    )


def _short(value: float, _position: int) -> str:
    """Write one tick of a log scale short enough to read.

    Args:
        value: The count the tick sits at.
        _position: Where the tick falls, ignored.

    Returns:
        The count, in thousands and up where it runs long.
    """
    return quantities.compact(value)

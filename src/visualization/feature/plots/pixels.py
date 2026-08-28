"""How many pixels one observation lands on a tile, instrument by instrument."""

from __future__ import annotations

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.ticker import FuncFormatter, MaxNLocator

from utils.maths import quantities
from visualization.common import panels, wording
from visualization.feature.picker import NO_TILE, TileView
from visualization.feature.stats import landed
from visualization.feature.stats.landed import Landed

# One panel per instrument set, each on a scale of its own, so height is per panel
PANEL_HEIGHT = 1.4

# The strip left clear above the panels, in inches, for the line naming the tile.
TITLE_BAND = 0.42

# How many places along the axis the observations are counted into.
BINS = 60

# A stem standing where the looks landed, as tall as there are of them, and the
# room left above the tallest so a point never sits on the panel above.
STEM_ALPHA = 0.35
STEM_WIDTH = 0.7
POINT_SIZE = 12
POINT_ALPHA = 0.65
HEADROOM = 1.25

# The room left past the furthest look, so the last stem stands clear of the edge.
MARGIN = 1.05

# How the pixels a strategy asks for are marked.
BAR_COLOUR = "#1a1a1a"
BAR_STYLE = (0, (4, 2))
BAR_WIDTH = 1.0

_TRACES = "traces"
_PIXELS = "px"
_NOTHING = "nothing on this tile"
_LANDED = "Pixels one observation lands on the tile"


def plot(chosen: TileView | None) -> widgets.Widget:
    """Draw what each instrument lands on the tile, one observation at a time.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when no tile is picked.
    """
    if chosen is None:
        return panels.unavailable(NO_TILE)
    drawn = landed.read(chosen)
    colours = panels.colours([one.label for one in drawn])
    tall = PANEL_HEIGHT * len(drawn) + TITLE_BAND
    figure, axes = plt.subplots(len(drawn), 1, figsize=(panels.FIGURE_WIDTH, tall))
    axes = np.atleast_1d(axes)
    for axis, one in zip(axes, drawn, strict=True):
        _panel(axis, one, colours[one.label])
    axes[-1].set_xlabel(_LANDED)
    figure.supylabel("Observations", fontsize=10)
    # The strip is measured in inches, so it holds however many panels there are
    above = TITLE_BAND / tall
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 1.0 - above))
    figure.text(
        0.01,
        1.0 - above / 2.0,
        f"{chosen.name}  -  pixels per observation",
        fontsize=12,
        va="center",
    )
    return panels.rendered(figure)


def _panel(axis: Axes, one: Landed, colour) -> None:
    """Draw a stem for every place the set's looks landed, on its own axis.

    Args:
        axis: The panel to draw on.
        one: What the set landed on the tile.
        colour: The colour the set is drawn in.

    Returns:
        None.
    """
    counts = np.asarray(one.counts, dtype=float)
    # The axis reaches the bar even where every look fell short of it
    top = max(float(counts.max()), one.bar) if counts.size else 0.0
    if top > 0.0:
        tallest = _looks(axis, counts, colour, top)
        if one.bar > 0.0:
            axis.axvline(
                one.bar,
                color=BAR_COLOUR,
                linestyle=BAR_STYLE,
                linewidth=BAR_WIDTH,
                zorder=3,
            )
        _reading(axis, one, counts)
        axis.set_xlim(0.0, top * MARGIN)
        axis.set_ylim(0.0, tallest * HEADROOM)
        axis.xaxis.set_major_formatter(
            FuncFormatter(lambda counted, _: quantities.compact(counted))
        )
        axis.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))
    else:
        panels.note(axis, _NOTHING)
        axis.set_xticks([])
    axis.set_ylabel(one.label, rotation=0, ha="right", va="center", fontsize=9)
    axis.tick_params(labelsize=8)
    axis.grid(axis="both", alpha=0.25, linewidth=0.5)
    axis.spines[["top", "right"]].set_visible(False)


def _looks(axis: Axes, counts: np.ndarray, colour, top: float) -> int:
    """Stand a stem where the looks landed, as tall as there are of them.

    Args:
        axis: The panel to draw on.
        counts: The pixels each of the set's observations landed.
        colour: The colour the set is drawn in.
        top: How far the axis runs, which the counting is spread over.

    Returns:
        How many observations the busiest place along the axis holds.
    """
    counted, edges = np.histogram(counts, bins=BINS, range=(0.0, top))
    middles = (edges[:-1] + edges[1:]) / 2.0
    standing = counted > 0
    at, high = middles[standing], counted[standing]
    axis.vlines(at, 0.0, high, color=colour, alpha=STEM_ALPHA, linewidth=STEM_WIDTH)
    axis.scatter(
        at,
        high,
        s=POINT_SIZE,
        alpha=POINT_ALPHA,
        color=colour,
        edgecolors="none",
        zorder=3,
    )
    return int(counted.max())


def _reading(axis: Axes, one: Landed, counts: np.ndarray) -> None:
    """Say what the panel holds, in the units the instrument counts in.

    Args:
        axis: The panel to write on.
        one: The instrument set the panel draws.
        counts: The pixels each of its observations landed.

    Returns:
        None.
    """
    unit = _TRACES if one.iid == wording.SOUNDER else _PIXELS
    axis.set_title(
        f"{counts.size:,} observations  -  "
        f"middle one lands {quantities.compact(float(np.median(counts)))} {unit}  -  "
        f"asked for {quantities.compact(one.bar)} {unit}",
        fontsize=8,
        color=panels.GREY,
        loc="left",
    )

"""How many pixels one observation lands on a tile, instrument by instrument."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.ticker import FuncFormatter

from utils.maths import quantities
from visualization.common import panels, wording
from visualization.feature.picker import NO_TILE, TileView
from visualization.feature.stats import landed
from visualization.feature.stats.landed import Landed

# One panel per instrument set, each on a scale of its own, so height is per panel
PANEL_HEIGHT = 1.55

# The strip left clear above the panels, in inches, for the line naming the tile.
TITLE_BAND = 0.42

# How many points one curve is drawn through.
CURVE_POINTS = 400
CURVE_WIDTH = 1.6
CURVE_FILL = 0.15

# How wide a bell is drawn where the observations agree too closely to spread one.
SMOOTHING = 0.02

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
    return _draw(landed.read(chosen), f"{chosen.name}  -  pixels per observation")


def _draw(drawn: Sequence[Landed], title: str) -> widgets.Widget:
    """Draw one panel per instrument set, none of them sharing a scale.

    Args:
        drawn: What each set landed on the tile, look by look.
        title: The line above the top panel.

    Returns:
        The figure as a widget.
    """
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
    figure.text(0.01, 1.0 - above / 2.0, title, fontsize=12, va="center")
    return panels.rendered(figure)


def _panel(axis: Axes, one: Landed, colour) -> None:
    """Draw one instrument set's counts as a bell over its own axis.

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
        across = np.linspace(0.0, top, CURVE_POINTS)
        bell = _bell(counts, across, top)
        axis.plot(across, bell, color=colour, linewidth=CURVE_WIDTH)
        axis.fill_between(across, bell, color=colour, alpha=CURVE_FILL, linewidth=0)
        _bar(axis, one.bar)
        _reading(axis, one, counts)
        axis.set_xlim(0.0, top)
        axis.set_ylim(bottom=0.0)
        axis.xaxis.set_major_formatter(FuncFormatter(_short))
    else:
        axis.text(
            0.5,
            0.5,
            _NOTHING,
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


def _bell(counts: np.ndarray, across: np.ndarray, top: float) -> np.ndarray:
    """Spread one set's counts into the bell they make along the axis.

    Args:
        counts: The pixels each of its observations landed.
        across: The points along the axis the bell is drawn through.
        top: How far the axis runs, which sets how wide a flat bell is drawn.

    Returns:
        How thickly the observations sit at each of those points.
    """
    spread = float(counts.std())
    # Silverman's rule, held open so counts that agree closely still draw as a bell
    width = max(1.06 * spread * counts.size**-0.2, top * SMOOTHING)
    standard = (across[:, None] - counts[None, :]) / width
    return np.exp(-0.5 * standard * standard).sum(axis=1) / counts.size


def _bar(axis: Axes, asked: float) -> None:
    """Mark the pixels the strategy asks before a look counts as one at all.

    Args:
        axis: The panel to draw on.
        asked: The pixels it asks of this set on this tile.

    Returns:
        None.
    """
    if asked <= 0.0:
        return
    axis.axvline(
        asked, color=BAR_COLOUR, linestyle=BAR_STYLE, linewidth=BAR_WIDTH, zorder=3
    )


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


def _short(value: float, _position: int) -> str:
    """Write one tick of an axis short enough to read.

    Args:
        value: The count the tick sits at.
        _position: Where the tick falls, ignored.

    Returns:
        The count, in thousands and up where it runs long.
    """
    return quantities.compact(value)

"""How much of a feature an instrument reached, against how big the feature is."""

from __future__ import annotations

from itertools import cycle

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from sampling.models.catalogue import CatalogueStats, InstrumentStats
from visualization.common import panels

_HEIGHT = 4.6

# How the points are drawn, since thousands of them sit on one panel.
_POINT = 9
_ALPHA = 0.18

# How many size bands the middle of each instrument is read over, and the least
# features a band needs before it is drawn.
_BANDS = 18
_LEAST = 5


def against_size(stats: CatalogueStats) -> widgets.Widget:
    """Draw the share of a feature each instrument reached against its size.

    Args:
        stats: What the catalogue index holds.

    Returns:
        The figure as a widget.
    """
    figure, axis = panels.board((panels.FIGURE_WIDTH, _HEIGHT))
    wheel = cycle(plt.cm.tab10.colors)
    for instrument, colour in zip(stats.instruments, wheel, strict=False):
        _draw(axis, instrument, colour)
    axis.set_xscale("log")
    axis.set_ylim(0.0, 1.02)
    axis.set_title(
        "How much of a feature was reached, against how big it is",
        fontsize=12,
        loc="left",
    )
    axis.set_xlabel("Ground the feature's bounding box holds (km2)")
    axis.set_ylabel("Ground the instrument reached")
    panels.tidy(axis, "y", "both")
    axis.legend(fontsize=9, frameon=False, loc="lower left")
    figure.tight_layout()
    return panels.rendered(figure)


def _draw(axis, instrument: InstrumentStats, colour: panels.Colour) -> None:
    """Draw one instrument as a feature apiece, with the middle of them over it.

    Args:
        axis: The panel to draw on, whose x axis runs over the feature sizes.
        instrument: What it holds of the dataset.
        colour: The colour to draw it in.

    Returns:
        None.
    """
    areas = np.array([one.area_km2 for one in instrument.reach])
    reached = np.array([one.covered_frac for one in instrument.reach])
    axis.scatter(areas, reached, s=_POINT, alpha=_ALPHA, color=colour, linewidths=0.0)
    middles, heights = _middle(areas, reached)
    axis.plot(
        middles,
        heights,
        color=colour,
        linewidth=1.8,
        marker="o",
        markersize=3.5,
        label=f"{instrument.iid}, middle of a size band",
        zorder=3,
    )


def _middle(areas: np.ndarray, reached: np.ndarray) -> tuple[list[float], list[float]]:
    """Read the median share reached over each band of feature sizes.

    Args:
        areas: How much ground each feature holds.
        reached: The share of it the instrument reached, in the same order.

    Returns:
        The middle size of each band busy enough to draw, and the share there.
    """
    edges = np.logspace(np.log10(areas.min()), np.log10(areas.max()), _BANDS + 1)
    placed = np.digitize(areas, edges[1:-1])
    middles, heights = [], []
    for band in range(_BANDS):
        held = placed == band
        if held.sum() < _LEAST:
            continue
        middles.append(float(np.median(areas[held])))
        heights.append(float(np.median(reached[held])))
    return middles, heights

"""How many pixels one observation lands, instrument by instrument."""

from __future__ import annotations

from itertools import cycle

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from sampling.models.catalogue import CatalogueStats, InstrumentStats
from visualization.common import panels, wording

# How many bars one instrument's distribution is drawn in.
_BARS = 40

_HEIGHT = 4.2


def distribution(stats: CatalogueStats) -> widgets.Widget:
    """Draw how many pixels one observation lands inside a feature.

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
    axis.set_title(
        "Pixels one observation lands inside a feature", fontsize=12, loc="left"
    )
    axis.set_xlabel("Pixels the observation lands, averaged over the feature")
    axis.set_ylabel("Features")
    axis.grid(axis="both", alpha=0.25, linewidth=0.5)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(fontsize=9, frameon=False)
    figure.tight_layout()
    return panels.rendered(figure)


def _draw(axis, instrument: InstrumentStats, colour: panels.Colour) -> None:
    """Draw one instrument's distribution over the features it reached.

    Args:
        axis: The panel to draw on, whose x axis runs over the pixel counts.
        instrument: What it holds of the dataset.
        colour: The colour to draw it in.

    Returns:
        None.
    """
    landed = [
        one.pixels_per_observation
        for one in instrument.reach
        if one.pixels_per_observation > 0.0
    ]
    if not landed:
        return
    axis.hist(
        landed,
        bins=_edges(landed),
        histtype="stepfilled",
        alpha=0.55,
        color=colour,
        edgecolor=colour,
        label=_named(instrument.iid),
    )


def _edges(landed: list[float]) -> np.ndarray:
    """Return the bar edges one distribution is counted into, evenly on a log scale.

    Args:
        landed: The pixels one observation lands, feature by feature.

    Returns:
        The edges in order, one more than there are bars.
    """
    return np.logspace(np.log10(min(landed)), np.log10(max(landed)), _BARS + 1)


def _named(iid: str) -> str:
    """Name one instrument in the key, saying where a pixel is not a picture element.

    Args:
        iid: The instrument.

    Returns:
        The name the key reads.
    """
    if iid == wording.SOUNDER:
        return f"{iid} (radargram columns)"
    return iid

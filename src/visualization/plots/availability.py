"""Where a feature's record is thickest across every instrument at once."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import date2num

from models.results import SetCoverage
from visualization import configs, panels
from visualization.plots import binning
from visualization.selectors.window import Window


def plot(coverage: Sequence[SetCoverage], window: Window) -> widgets.Widget:
    """Draw the mean share of the instruments' records falling in each bin.

    A set is scored on the ground it covered rather than on how many times it
    looked, and each is scaled by its own total, so a narrow sounder and a wide
    camera weigh the same. The weakest set is filled in under the mean, so a
    bin one instrument carries alone reads apart from one they all reach.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range to bin over, one bin per column of it.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    scored = [entry for entry in coverage if _total(entry) > 0]
    if not scored:
        return panels.unavailable("No instrument set covered any ground here.")
    edges = binning.edges(coverage, window)
    shares = np.array([_shares(entry, window, edges) for entry in scored])
    span = date2num(edges)
    figure, axis = plt.subplots(figsize=configs.AVAILABILITY_FIGURE_SIZE)
    axis.stairs(
        shares.mean(axis=0),
        span,
        fill=True,
        color=configs.AVAILABILITY_COLOUR,
        alpha=configs.AVAILABILITY_MEAN_ALPHA,
        label=f"mean across the {len(scored)} sets",
    )
    axis.stairs(
        shares.min(axis=0),
        span,
        fill=True,
        color=configs.AVAILABILITY_COLOUR,
        alpha=configs.AVAILABILITY_FLOOR_ALPHA,
        label="the weakest set",
    )
    axis.set_title(
        f"{panels.title(coverage)}  -  data available per {binning.name()}",
        fontsize=12,
        loc="left",
    )
    axis.set_xlabel("Observation start time")
    axis.set_ylabel(f"Share of a set's ground\nreached in the {binning.name()}")
    axis.set_xlim(span[0], span[-1])
    axis.set_ylim(bottom=0)
    axis.xaxis_date()
    panels.tidy(axis, percent="y", grid="both", decimals=None)
    axis.legend(fontsize=9, loc="upper left", frameon=False)
    figure.tight_layout()
    return panels.rendered(figure)


def _total(entry: SetCoverage) -> float:
    """Return the ground one instrument set reached across its whole record.

    Args:
        entry: The instrument set being scored.

    Returns:
        The summed overlap of all of its observations, which is zero for a set
        that observed nothing and for one whose footprints only grazed the
        feature.
    """
    return sum(event.own_km2 for event in entry.events)


def _shares(
    entry: SetCoverage, window: Window, edges: Sequence[datetime]
) -> np.ndarray:
    """Score one instrument set's covered ground in each time bin.

    The total is taken over the whole record rather than over the window, so
    narrowing the window lowers the curve instead of rescaling it, and the area
    under it reads as the share of the record the window keeps.

    Args:
        entry: The instrument set being scored, which covered some ground.
        window: The date range, which excludes what falls outside it.
        edges: The bin edges, in order.

    Returns:
        One share per bin, in the same order.
    """
    visible = window.visible(entry.events)
    binned, _ = np.histogram(
        [date2num(event.t_start) for event in visible],
        bins=date2num(edges),
        weights=[event.own_km2 for event in visible],
    )
    return binned / _total(entry)

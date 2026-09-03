"""How much of the ground each instrument has reached over time, and in total."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt

from analysis.visualization.common import panels, series
from analysis.visualization.common.picker import Coverage
from analysis.visualization.common.series import Series

# How an instrument set with nothing to draw is drawn anyway.
UNOBSERVED_LINESTYLE = (0, (1, 3))

# The running curve beside the totals, and how the width is split between them
CUMULATIVE_FIGURE_SIZE = (13, 5)
CUMULATIVE_WIDTH_RATIOS = [3, 1]

_GROUND = "Share of the feature covered so far"


def plot(coverage: Coverage) -> widgets.Widget:
    """Draw the running coverage of the whole feature, beside its total.

    Args:
        coverage: The feature on show, as the instrument sets it holds.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    drawn = series.over_feature(coverage)
    colours = panels.colours([one.label for one in drawn])
    figure, (running, bars) = plt.subplots(
        1,
        2,
        figsize=CUMULATIVE_FIGURE_SIZE,
        gridspec_kw={"width_ratios": CUMULATIVE_WIDTH_RATIOS},
    )
    last = max(one.last for one in drawn)
    for one in drawn:
        if one.observed:
            times = [one.times[0]] + list(one.times)
            fractions = [0.0] + list(one.running)
            if times[-1] < last:
                times.append(last)
                fractions.append(fractions[-1])
        else:
            times, fractions = [one.first, last], [0.0, 0.0]
        running.plot(
            times,
            fractions,
            linewidth=1.8,
            linestyle="-" if one.observed else UNOBSERVED_LINESTYLE,
            color=colours[one.label],
            label=(
                f"{one.label}  ({one.covered:.1%})"
                if one.observed
                else f"{one.label}  ({one.reason})"
            ),
        )
    title = f"{panels.title(coverage)}  -  cumulative coverage"
    running.set_title(title, fontsize=12, loc="left")
    running.set_xlabel("Observation start time")
    running.set_ylabel(_GROUND)
    running.set_ylim(0, 1.05)
    running.set_xlim(right=last)
    panels.tidy(running, percent="y", grid="both")
    running.legend(fontsize=9, loc="upper left", frameon=False)
    _totals(bars, drawn, colours)
    figure.tight_layout()
    return panels.rendered(figure)


def _totals(axis, drawn: Sequence[Series], colours: dict) -> None:
    """Draw where each instrument set ended up.

    Args:
        axis: The panel to draw on.
        drawn: What each set observed of the ground on show.
        colours: The colour of each set, keyed by label.

    Returns:
        None.
    """
    ranked = list(drawn)[::-1]
    axis.barh(
        [one.label for one in ranked],
        [one.covered for one in ranked],
        color=[colours[one.label] for one in ranked],
    )
    axis.set_title("Total covered", fontsize=11, loc="left")
    axis.set_xlim(0, 1.05)
    axis.tick_params(labelsize=9)
    panels.tidy(axis, percent="x", grid="x")

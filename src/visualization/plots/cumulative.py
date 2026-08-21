"""How much of a feature each instrument has reached over time, and in total."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import ipywidgets as widgets
import matplotlib.pyplot as plt

from models.results import SetCoverage
from visualization import panels

# How an instrument set with nothing to draw is drawn anyway.
UNOBSERVED_LINESTYLE = (0, (1, 3))

# The running curve beside the totals, and how the width is split between them
CUMULATIVE_FIGURE_SIZE = (13, 5)
CUMULATIVE_WIDTH_RATIOS = [3, 1]


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Draw the running coverage per instrument beside its final total.

    Args:
        coverage: The feature's instrument sets, widest coverage first.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    colours = panels.colours(coverage)
    figure, (running, bars) = plt.subplots(
        1,
        2,
        figsize=CUMULATIVE_FIGURE_SIZE,
        gridspec_kw={"width_ratios": CUMULATIVE_WIDTH_RATIOS},
    )
    last = max(instrument.summary.t_last for instrument in coverage)
    for instrument in coverage:
        times, fractions = _points(instrument, last)
        running.plot(
            times,
            fractions,
            linewidth=1.8,
            linestyle="-" if instrument.observed else UNOBSERVED_LINESTYLE,
            color=colours[instrument.label],
            label=(
                f"{instrument.label}  ({instrument.summary.covered_frac:.1%})"
                if instrument.observed
                else f"{instrument.label}  ({instrument.reason})"
            ),
        )
    running.set_title(
        f"{panels.title(coverage)}  -  cumulative coverage", fontsize=12, loc="left"
    )
    running.set_xlabel("Observation start time")
    running.set_ylabel("Share of the feature covered so far")
    running.set_ylim(0, 1.05)
    running.set_xlim(right=last)
    panels.tidy(running, percent="y", grid="both")
    running.legend(fontsize=9, loc="upper left", frameon=False)
    _totals(bars, coverage, colours)
    figure.tight_layout()
    return panels.rendered(figure)


def _points(instrument: SetCoverage, last: datetime) -> tuple[list, list[float]]:
    """Return one instrument set's running coverage, rooted at zero.

    Args:
        instrument: The instrument set being drawn.
        last: When the latest observation on the panel was taken.

    Returns:
        The times and the share covered by then, in chronological order.
    """
    if not instrument.observed:
        return [instrument.summary.t_first, last], [0.0, 0.0]
    first = instrument.events[0].t_start
    times = [first] + [observation.t_start for observation in instrument.events]
    fractions = [0.0] + [observation.cum_frac for observation in instrument.events]
    if times[-1] < last:
        times.append(last)
        fractions.append(fractions[-1])
    return times, fractions


def _totals(axis, coverage: Sequence[SetCoverage], colours: dict) -> None:
    """Draw where each instrument set ended up.

    Args:
        axis: The panel to draw on.
        coverage: The feature's instrument sets, widest coverage first.
        colours: The colour of each set, keyed by label.

    Returns:
        None.
    """
    ranked = list(coverage)[::-1]
    axis.barh(
        [instrument.label for instrument in ranked],
        [instrument.summary.covered_frac for instrument in ranked],
        color=[colours[instrument.label] for instrument in ranked],
    )
    axis.set_title("Total covered", fontsize=11, loc="left")
    axis.set_xlim(0, 1.05)
    axis.tick_params(labelsize=9)
    panels.tidy(axis, percent="x", grid="x")

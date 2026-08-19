"""How much of a feature each instrument has reached over time, and in total."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import ipywidgets as widgets
import matplotlib.pyplot as plt

from models.results import SetCoverage
from visualization import configs, panels
from visualization.window import Window


def plot(coverage: Sequence[SetCoverage], window: Window) -> widgets.Widget:
    """Draw the running coverage per instrument beside its final total.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range the running curve is shown over. The curves
            themselves are not recomputed, so one entering the window part way
            up keeps the level it had already reached.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    colours = panels.colours(coverage)
    figure, (running, bars) = plt.subplots(
        1,
        2,
        figsize=configs.CUMULATIVE_FIGURE_SIZE,
        gridspec_kw={"width_ratios": configs.CUMULATIVE_WIDTH_RATIOS},
    )
    last = max(entry.summary.t_last for entry in coverage)
    for entry in coverage:
        times, fractions = _points(entry, last)
        running.plot(
            times,
            fractions,
            linewidth=1.8,
            linestyle="-" if entry.observed else configs.UNOBSERVED_LINESTYLE,
            color=colours[entry.label],
            label=(
                f"{entry.label}  ({entry.summary.covered_frac:.1%})"
                if entry.observed
                else f"{entry.label}  ({entry.reason})"
            ),
        )
    running.set_title(
        f"{panels.title(coverage)}  -  cumulative coverage", fontsize=12, loc="left"
    )
    running.set_xlabel("Observation start time")
    running.set_ylabel("Share of the feature covered so far")
    running.set_ylim(0, 1.05)
    running.set_xlim(left=window.start, right=window.end or last)
    panels.tidy(running, percent="y", grid="both")
    running.legend(fontsize=9, loc="upper left", frameon=False)
    _totals(bars, coverage, colours)
    figure.tight_layout()
    return panels.rendered(figure)


def _points(entry: SetCoverage, last: datetime) -> tuple[list, list[float]]:
    """Return one instrument set's running coverage, rooted at zero.

    Args:
        entry: The instrument set being drawn.
        last: When the latest observation on the panel was taken.

    Returns:
        The times and the share covered by then, in chronological order.
    """
    if not entry.observed:
        return [entry.summary.t_first, last], [0.0, 0.0]
    first = entry.events[0].t_start
    times = [first] + [event.t_start for event in entry.events]
    fractions = [0.0] + [event.cum_frac for event in entry.events]
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
        [entry.label for entry in ranked],
        [entry.summary.covered_frac for entry in ranked],
        color=[colours[entry.label] for entry in ranked],
    )
    axis.set_title("Total covered", fontsize=11, loc="left")
    axis.set_xlim(0, 1.05)
    axis.tick_params(labelsize=9)
    panels.tidy(axis, percent="x", grid="x")

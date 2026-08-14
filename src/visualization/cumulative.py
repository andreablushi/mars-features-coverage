"""How much of a feature each instrument has reached over time, and in total."""

from __future__ import annotations

from collections.abc import Sequence

import ipywidgets as widgets
import matplotlib.pyplot as plt
<<<<<<< Updated upstream:src/visualization/cumulative.py
=======
from models.results import SetCoverage
>>>>>>> Stashed changes:src/visualization/plots/cumulative.py

from analysis.models.coverage import SetCoverage
from visualization import configs, panels


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Draw the running coverage per instrument beside its final total.

    Args:
        coverage: The feature's instrument sets, widest coverage first.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    coverage = [entry for entry in coverage if entry.summary.covered_frac is not None]
    if not coverage:
        return panels.unavailable(configs.NO_UNION)
    colours = panels.colours(coverage)
    figure, (curve, bars) = plt.subplots(
        1,
        2,
        figsize=configs.CUMULATIVE_FIGURE_SIZE,
        gridspec_kw={"width_ratios": configs.CUMULATIVE_WIDTH_RATIOS},
    )
    _curves(curve, coverage, colours)
    curve.set_title(
        f"{panels.title(coverage)}  -  cumulative coverage", fontsize=12, loc="left"
    )
    _totals(bars, coverage, colours)
    figure.tight_layout()
    return panels.rendered(figure)


def _curves(axis, coverage: Sequence[SetCoverage], colours: dict) -> None:
    """Draw one running coverage curve per instrument set.

    Args:
        axis: The panel to draw on.
        coverage: The feature's instrument sets, widest coverage first.
        colours: The colour of each set, keyed by label.

    Returns:
        None.
    """
    for entry in coverage:
        times, fractions = _curve(entry)
        axis.plot(
            times,
            fractions,
            linewidth=1.8,
            color=colours[entry.label],
            label=f"{entry.label}  ({entry.summary.covered_frac:.1%})",
        )
    axis.set_xlabel("Observation start time")
    axis.set_ylabel("Share of the feature covered so far")
    axis.set_ylim(0, 1.05)
    panels.tidy(axis, percent="y", grid="both")
    axis.legend(fontsize=9, loc="upper left", frameon=False)


def _curve(entry: SetCoverage) -> tuple[list, list[float]]:
    """Return one instrument set's running coverage, rooted at zero.

    The set covered nothing before its first observation, so the curve starts
    there rather than at whatever that first observation happened to reach.

    Args:
        entry: The instrument set being drawn.

    Returns:
        The times and the share covered by then, in chronological order.
    """
    first = entry.events[0].t_start
    times = [first] + [event.t_start for event in entry.events]
    fractions = [0.0] + [event.cum_frac for event in entry.events]
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

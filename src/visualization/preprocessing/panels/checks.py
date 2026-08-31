"""What each step changed, and whether it changed more than it should have."""

from __future__ import annotations

import warnings

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from preprocessing.crism import configs
from preprocessing.crism.models.strip import Strip
from visualization.common import panels, tables
from visualization.preprocessing.picker import Cleaned

NO_STRIP = "Pick an observation above and press Clean to fill this in."

FIGURE_SIZE = (panels.FIGURE_WIDTH, 7.0)

_HEADINGS = (
    "Step",
    "Values moved",
    "Share",
    "Median move",
    "Worst move",
    "Newly unreadable",
)

# How many voxels the before-against-after scatter is drawn from.
SAMPLED = 40_000

# The CO2 band the atmosphere carves into every spectrum, in nanometres.
CO2_NM = 2000.0

# How close a band has to be to count as sitting on a marked wavelength.
NEAR_NM = 60.0


def accounting(chosen: Cleaned | None) -> widgets.Widget:
    """Tabulate how much each step of the cleaning changed.

    Args:
        chosen: The cleaned observation, or None while none is picked.

    Returns:
        The table, or the grey panel when nothing is loaded.
    """
    if chosen is None:
        return panels.unavailable(NO_STRIP)

    rows = []
    for before, after in zip(chosen.stages, chosen.stages[1:], strict=False):
        moved = after.touched(before)
        count = int(moved.sum())
        drift = np.abs(after.cube - before.cube)[moved] if count else np.zeros(1)
        rows.append(
            (
                after.name,
                f"{count:,}",
                f"{count / moved.size * 100:.2f}%",
                f"{np.median(drift):.5f}" if count else "-",
                f"{drift.max():.4f}" if count else "-",
                f"{int(after.lost(before).sum()):,}",
            )
        )
    return tables.written("What each step changed", _HEADINGS, rows)


def plot(chosen: Cleaned | None) -> widgets.Widget:
    """Draw the checks that catch a cleaning doing too much or too little.

    Args:
        chosen: The cleaned observation, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if chosen is None:
        return panels.unavailable(NO_STRIP)

    masked, destriped = chosen.stages[1], chosen.stages[2]
    figure, ((before, after), (physics, kept)) = plt.subplots(2, 2, figsize=FIGURE_SIZE)

    _columns(before, masked.cube, chosen.strip, "before destriping")
    _columns(after, destriped.cube, chosen.strip, "after destriping")
    _physics(physics, chosen)
    _preserved(kept, masked.cube, chosen.final.cube)

    figure.suptitle(
        f"{chosen.strip.product_id}  -  did the cleaning do the right amount",
        fontsize=12,
        x=0.01,
        ha="left",
    )
    figure.tight_layout()
    return panels.rendered(figure)


def _columns(axis: plt.Axes, cube: np.ndarray, strip: Strip, title: str) -> None:
    """Draw the average spectrum of every live detector column.

    Args:
        axis: The axis to draw on.
        cube: The spectra at this stage.
        strip: The observation, for its band centres and live columns.
        title: What the panel shows.

    Returns:
        None.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        averaged = np.nanmean(cube, axis=0)
        spread = float(np.nanmean(np.nanstd(averaged[strip.columns], axis=0)))
    for column in np.flatnonzero(strip.columns):
        axis.plot(
            strip.wavelengths, averaged[column], color=panels.GREY, alpha=0.35, lw=0.6
        )
    axis.set_xlabel("Wavelength, nm")
    axis.set_ylabel("I/F")
    axis.set_title(f"Column averages, {title}", fontsize=10, loc="left")
    axis.grid(alpha=0.25, linewidth=0.5)
    panels.note(axis, f"mean spread between columns {spread:.5f}")


def _physics(axis: plt.Axes, chosen: Cleaned) -> None:
    """Draw the average spectrum against the features it has to show.

    Args:
        axis: The axis to draw on.
        chosen: The cleaned observation.

    Returns:
        None.
    """
    centres = chosen.strip.wavelengths
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        average = np.nanmean(chosen.final.cube, axis=(0, 1))
    axis.plot(centres, average, color=panels.KEPT, linewidth=1.2)
    axis.axvline(CO2_NM, color=panels.REFUSED, linewidth=1.0, linestyle="--")
    opaque_from, opaque_to = configs.OPAQUE_NM
    axis.axvspan(opaque_from, opaque_to, color=panels.REFUSED, alpha=0.12)
    axis.set_xlabel("Wavelength, nm")
    axis.set_ylabel("I/F")
    axis.set_title("Average spectrum against known features", fontsize=10, loc="left")
    axis.grid(alpha=0.25, linewidth=0.5)

    band = int(np.argmin(np.abs(centres - CO2_NM)))
    sits = abs(centres[band] - CO2_NM) <= NEAR_NM
    shoulders = [
        int(np.argmin(np.abs(centres - CO2_NM + offset))) for offset in (-200.0, 200.0)
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        depth = float(np.nanmean(average[shoulders]) - average[band])
    panels.note(
        axis,
        f"CO2 band {'found' if sits else 'NOT found'} at {centres[band]:.0f} nm, "
        f"{depth:+.4f} below its shoulders.\n"
        "It should be a dip: nothing here corrects for the atmosphere.",
    )


def _preserved(axis: plt.Axes, before: np.ndarray, after: np.ndarray) -> None:
    """Draw what the cleaning did to the values it kept.

    Args:
        axis: The axis to draw on.
        before: The cube before any filtering.
        after: The cube the cleaning ended with.

    Returns:
        None.
    """
    both = np.isfinite(before) & np.isfinite(after)
    lit = np.flatnonzero(both.ravel())
    if not lit.size:
        panels.note(axis, "nothing readable on both sides")
        return
    rng = np.random.default_rng(0)
    drawn = rng.choice(lit, size=min(SAMPLED, lit.size), replace=False)
    left, right = before.ravel()[drawn], after.ravel()[drawn]
    axis.scatter(left, right, s=2, alpha=0.15, color=panels.GREY)
    limit = float(max(left.max(), right.max()))
    axis.plot([0, limit], [0, limit], color=panels.KEPT, linewidth=1.0)
    axis.set_xlabel("Before filtering")
    axis.set_ylabel("After cleaning")
    axis.set_title("Every kept value, against itself", fontsize=10, loc="left")
    axis.grid(alpha=0.25, linewidth=0.5)
    panels.note(
        axis,
        f"correlation {np.corrcoef(left, right)[0, 1]:.5f}, "
        f"{100 * float(np.mean(left != right)):.2f}% moved.\n"
        "Points far off the line are what the cleaning rewrote.",
    )

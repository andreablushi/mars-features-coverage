"""Single spectra at every stage, which is where over-cleaning shows first."""

from __future__ import annotations

import warnings

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from visualization.common import panels
from visualization.preprocessing.picker import Cleaned

NO_STRIP = "Pick an observation above and press Clean to fill this in."
NOTHING_READABLE = "Nothing in this observation is readable enough to draw."

FIGURE_SIZE = (panels.FIGURE_WIDTH, 6.4)

# How many pixels are drawn beside the average.
SHOWN = 3

# A pixel is worth drawing when this much of its spectrum survives.
READABLE = 0.9


def plot(chosen: Cleaned | None, seed: int | None = 0) -> widgets.Widget:
    """Draw a few spectra as every stage of the cleaning left them.

    Args:
        chosen: The cleaned observation, or None while none is picked.
        seed: Fixes which pixels are drawn, or None to vary them.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if chosen is None:
        return panels.unavailable(NO_STRIP)

    picked = _pixels(chosen, seed)
    if not picked:
        return panels.unavailable(NOTHING_READABLE)

    centres = chosen.strip.wavelengths
    shades = panels.colours([stage.name for stage in chosen.stages])
    figure, axes = plt.subplots(2, 2, figsize=FIGURE_SIZE)
    flat = axes.ravel()

    for axis, (line, sample) in zip(flat, picked, strict=False):
        for stage in chosen.stages:
            axis.plot(
                centres,
                stage.cube[line, sample, :],
                color=shades[stage.name],
                linewidth=1.0,
                label=stage.name,
            )
        _frame(axis, f"line {line}, sample {sample}")

    average = flat[len(picked)]
    for stage in chosen.stages:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            average.plot(
                centres,
                np.nanmean(stage.cube, axis=(0, 1)),
                color=shades[stage.name],
                linewidth=1.2,
                label=stage.name,
            )
    _frame(average, "average over the whole strip")

    handles, _ = flat[0].get_legend_handles_labels()
    panels.key_below(figure, handles)
    figure.suptitle(
        f"{chosen.strip.product_id}  -  spectra at every stage",
        fontsize=12,
        x=0.01,
        ha="left",
    )
    figure.tight_layout()
    return panels.rendered(figure)


def _frame(axis: plt.Axes, title: str) -> None:
    """Label and grid one spectrum panel.

    Args:
        axis: The axis to style.
        title: What the panel shows.

    Returns:
        None.
    """
    axis.set_xlabel("Wavelength, nm")
    axis.set_ylabel("I/F")
    axis.set_title(title, fontsize=10, loc="left")
    axis.grid(alpha=0.25, linewidth=0.5)


def _pixels(chosen: Cleaned, seed: int | None) -> list[tuple[int, int]]:
    """Pick a few pixels whose spectra mostly survived the cleaning.

    Args:
        chosen: The cleaned observation.
        seed: Fixes the draw, or None to vary it.

    Returns:
        The pixels as line and sample pairs, which may be fewer than asked for.
    """
    kept = 1.0 - chosen.final.mask.mean(axis=-1)
    lines, samples = np.nonzero(kept >= READABLE)
    if not lines.size:
        return []
    rng = np.random.default_rng(seed)
    chose = rng.choice(lines.size, size=min(SHOWN, lines.size), replace=False)
    return [(int(lines[one]), int(samples[one])) for one in chose]

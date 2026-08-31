"""Where the bands sit, and which of them the cleaning refuses to use.

Spectral smile is not drawn here. The band table is one centre per band, taken
once from the mode's wavelength file, so the per-column spread that smile
causes is not carried and cannot be shown. That is deliberate: at this
sampling the spread is about a quarter of a channel, and a ratio taken down a
detector column divides it out.
"""

from __future__ import annotations

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from visualization.common import panels
from visualization.preprocessing.picker import Cleaned

NO_STRIP = "Pick an observation above and press Clean to fill this in."

FIGURE_SIZE = (panels.FIGURE_WIDTH, 3.6)

# How far apart two neighbouring centres may be before the gap is called one.
GAP_NM = 100.0


def plot(chosen: Cleaned | None) -> widgets.Widget:
    """Draw where the bands sit and how far apart they are.

    Args:
        chosen: The cleaned observation, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if chosen is None:
        return panels.unavailable(NO_STRIP)

    strip = chosen.strip
    centres, usable = strip.wavelengths, strip.bands
    figure, (placed, spaced) = plt.subplots(1, 2, figsize=FIGURE_SIZE)

    index = np.arange(centres.size)
    placed.plot(index, centres, color=panels.GREY, linewidth=0.8, zorder=1)
    placed.scatter(index[usable], centres[usable], s=14, color=panels.KEPT, zorder=2)
    placed.scatter(
        index[~usable],
        centres[~usable],
        s=30,
        color=panels.REFUSED,
        marker="x",
        zorder=3,
    )
    placed.set_xlabel("Band")
    placed.set_ylabel("Centre, nm")
    placed.set_title("Band centres, ascending", fontsize=10, loc="left")
    placed.grid(alpha=0.25, linewidth=0.5)
    rising = bool(np.all(np.diff(centres) > 0))
    panels.note(placed, "ascending" if rising else "NOT ascending, the order is wrong")

    gaps = np.diff(centres)
    spaced.bar(index[1:], gaps, color=panels.GREY, width=0.9)
    spaced.axhline(strip.spacing_nm, color=panels.KEPT, linewidth=1.0, linestyle="--")
    spaced.set_xlabel("Band")
    spaced.set_ylabel("Gap to the band below, nm")
    spaced.set_title("Spacing", fontsize=10, loc="left")
    spaced.grid(axis="y", alpha=0.25, linewidth=0.5)
    panels.note(
        spaced,
        f"median {strip.spacing_nm:.1f} nm, {int((gaps > GAP_NM).sum())} gaps over "
        f"{GAP_NM:.0f} nm where channels were never downlinked",
    )

    dead = np.flatnonzero(~strip.columns)
    figure.suptitle(
        f"{strip.product_id}  -  bands and detector columns"
        f"   (dead columns: {', '.join(str(one) for one in dead) or 'none'})",
        fontsize=12,
        x=0.01,
        ha="left",
    )
    figure.tight_layout()
    return panels.rendered(figure)

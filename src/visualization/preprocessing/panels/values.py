"""What the numbers look like, and where the unreadable ones sit."""

from __future__ import annotations

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from preprocessing.crism import configs
from visualization.common import panels
from visualization.preprocessing.picker import Cleaned

NO_STRIP = "Pick an observation above and press Clean to fill this in."

FIGURE_SIZE = (panels.FIGURE_WIDTH, 7.0)

# How many bars the value histogram is drawn with.
BINS = 80


def plot(chosen: Cleaned | None) -> widgets.Widget:
    """Draw the spread of the values and the shape of what is unreadable.

    Args:
        chosen: The cleaned observation, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if chosen is None:
        return panels.unavailable(NO_STRIP)

    raw, final = chosen.stages[0], chosen.final
    figure, ((spread, footprint), (down, across)) = plt.subplots(
        2, 2, figsize=FIGURE_SIZE
    )

    _spread(spread, raw.cube, final.cube)
    _footprint(footprint, final.mask)
    _per_column(down, final.mask, chosen.strip.columns)
    _per_band(across, final.mask, chosen.strip.wavelengths)

    figure.suptitle(
        f"{chosen.strip.product_id}  -  values and what cannot be read",
        fontsize=12,
        x=0.01,
        ha="left",
    )
    figure.tight_layout()
    return panels.rendered(figure)


def _spread(axis: plt.Axes, raw: np.ndarray, final: np.ndarray) -> None:
    """Draw the spread of the readable values, and count what was thrown out.

    Args:
        axis: The axis to draw on.
        raw: The cube as it came off disk.
        final: The cube the cleaning ended with.

    Returns:
        None.
    """
    readable = final[np.isfinite(final)]
    if readable.size:
        axis.hist(readable, bins=BINS, color=panels.KEPT)
    axis.set_yscale("log")
    axis.set_xlabel("I/F")
    axis.set_ylabel("Voxels")
    axis.set_title("Values after cleaning", fontsize=10, loc="left")
    axis.grid(axis="y", alpha=0.25, linewidth=0.5)

    with np.errstate(invalid="ignore"):
        low = int((raw < configs.IF_MIN).sum())
        high = int(((raw > configs.IF_MAX) & (raw != configs.FILL)).sum())
    fill = int((raw == configs.FILL).sum())
    panels.note(
        axis,
        f"as read: {low:,} below 0, {high:,} above 1, {fill:,} fill.\n"
        f"crism_ml would have kept every one of the {low:,} negatives.",
    )


def _footprint(axis: plt.Axes, mask: np.ndarray) -> None:
    """Draw how much of each pixel's spectrum is unreadable.

    Args:
        axis: The axis to draw on.
        mask: Which voxels hold no usable measurement.

    Returns:
        None.
    """
    image = axis.imshow(
        mask.mean(axis=-1), aspect="auto", cmap="magma", vmin=0.0, vmax=1.0
    )
    axis.set_xlabel("Sample")
    axis.set_ylabel("Line")
    axis.set_title("Share of each spectrum unreadable", fontsize=10, loc="left")
    axis.figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)


def _per_column(axis: plt.Axes, mask: np.ndarray, columns: np.ndarray) -> None:
    """Draw how much each detector column cannot read.

    Args:
        axis: The axis to draw on.
        mask: Which voxels hold no usable measurement.
        columns: Which detector columns carry a wavelength calibration.

    Returns:
        None.
    """
    share = mask.mean(axis=(0, 2))
    index = np.arange(share.size)
    axis.bar(index[columns], share[columns], color=panels.KEPT, width=0.9)
    axis.bar(index[~columns], share[~columns], color=panels.REFUSED, width=0.9)
    axis.set_xlabel("Detector column")
    axis.set_ylabel("Share unreadable")
    axis.set_title("By detector column", fontsize=10, loc="left")
    axis.grid(axis="y", alpha=0.25, linewidth=0.5)
    panels.note(
        axis,
        "red columns carry no wavelength. They should stand out here too,\n"
        "which is the check that the hardcoded list still matches the data.",
    )


def _per_band(axis: plt.Axes, mask: np.ndarray, centres: np.ndarray) -> None:
    """Draw how much each band cannot read.

    Args:
        axis: The axis to draw on.
        mask: Which voxels hold no usable measurement.
        centres: The band centres in nanometres.

    Returns:
        None.
    """
    axis.plot(centres, mask.mean(axis=(0, 1)), color=panels.GREY, marker="o", ms=3)
    opaque_from, opaque_to = configs.OPAQUE_NM
    axis.axvspan(opaque_from, opaque_to, color=panels.REFUSED, alpha=0.12)
    axis.axvspan(
        configs.THERMAL_NM,
        max(centres.max(), configs.THERMAL_NM) + 1,
        color=panels.REFUSED,
        alpha=0.12,
    )
    axis.set_xlabel("Wavelength, nm")
    axis.set_ylabel("Share unreadable")
    axis.set_title("By band", fontsize=10, loc="left")
    axis.grid(alpha=0.25, linewidth=0.5)

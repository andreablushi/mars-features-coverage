"""The strip as a false colour image, before and after the cleaning.

Ported from crism_ml's `plot.get_false_colors`, which takes a median around
three chosen channels, normalises them, and stretches each one.

Differs from crism_ml:
  - The three channels are chosen by wavelength rather than by index, since the
    indices 233, 103 and 20 belong to its band table. They come out at the same
    wavelengths: about 2556, 1697 and 1152 nm.
  - The median window is given in nanometres, for the same reason the despiking
    windows are.
  - The medians and the normalisation ignore NaN, since unreadable voxels are
    left as NaN rather than filled.
"""

from __future__ import annotations

import warnings

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np

from preprocessing.crism import banding, configs
from visualization.common import panels
from visualization.preprocessing.picker import Cleaned

NO_STRIP = "Pick an observation above and press Clean to fill this in."

FIGURE_SIZE = (panels.FIGURE_WIDTH, 6.0)

# How much of each tail the stretch clips, as a percentage.
CLIP = 2.0


def plot(chosen: Cleaned | None) -> widgets.Widget:
    """Draw the strip in false colour as it came in and as it came out.

    Args:
        chosen: The cleaned observation, or None while none is picked.

    Returns:
        The figure as a widget, or the grey panel when nothing is loaded.
    """
    if chosen is None:
        return panels.unavailable(NO_STRIP)

    strip = chosen.strip
    figure, axes = plt.subplots(1, 2, figsize=FIGURE_SIZE)
    for axis, stage in ((axes[0], chosen.stages[1]), (axes[1], chosen.final)):
        axis.imshow(rendered_image(stage.cube, strip.wavelengths), aspect="auto")
        axis.set_title(stage.name, fontsize=10, loc="left")
        axis.set_xlabel("Sample")
        axis.set_ylabel("Line")

    red, green, blue = configs.FALSE_COLOUR_NM
    figure.suptitle(
        f"{strip.product_id}  -  false colour, red {red:.0f} nm, "
        f"green {green:.0f} nm, blue {blue:.0f} nm",
        fontsize=12,
        x=0.01,
        ha="left",
    )
    figure.tight_layout()
    return panels.rendered(figure)


def rendered_image(cube: np.ndarray, centres: np.ndarray) -> np.ndarray:
    """Turn a cube into a stretched false colour image.

    Args:
        cube: The spectra, lines by samples by bands.
        centres: The band centres in nanometres.

    Returns:
        The image as lines by samples by three, between zero and one.
    """
    size = banding.channels(
        configs.FALSE_COLOUR_WINDOW_NM, float(np.median(np.diff(centres)))
    )
    half = size // 2
    planes = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for wanted in configs.FALSE_COLOUR_NM:
            band = int(np.argmin(np.abs(centres - wanted)))
            window = cube[..., max(band - half, 0) : band + half + 1]
            planes.append(np.nanmedian(window, axis=-1))
    return np.stack([_stretched(one) for one in planes], axis=-1)


def _stretched(plane: np.ndarray) -> np.ndarray:
    """Scale one colour plane to fill the range, clipping both tails.

    Args:
        plane: One channel of the image, holding NaN where it is unreadable.

    Returns:
        The channel between zero and one, with unreadable pixels left black.
    """
    readable = plane[np.isfinite(plane)]
    if not readable.size:
        return np.zeros(plane.shape, dtype=np.float32)
    low, high = np.percentile(readable, [CLIP, 100.0 - CLIP])
    if high <= low:
        return np.zeros(plane.shape, dtype=np.float32)
    with np.errstate(invalid="ignore"):
        scaled = np.clip((plane - low) / (high - low), 0.0, 1.0)
    return np.nan_to_num(scaled, nan=0.0).astype(np.float32)

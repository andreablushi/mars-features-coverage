"""Saying which cells of a cube are not measurements, and filling them."""

from __future__ import annotations

import numpy as np

from preprocessing.crism import configs
from preprocessing.crism.fetching import bands_calibration
from preprocessing.crism.models.mask import Mask


def bad_pixels(
    cube: np.ndarray, table: np.ndarray, detector: str
) -> tuple[np.ndarray, Mask]:
    """Fill everything one cube holds that is not a measurement.

    Args:
        cube: The values as lines by samples by bands, ordered by wavelength.
        table: The centre wavelength of every column and band, in that order.
        detector: Which detector, `l` for infrared or `s` for visible, which
            picks the window.

    Returns:
        The cube with every refused cell replaced by the mean of what is kept,
        and the mask saying where that happened.

    Raises:
        KeyError: When no window is configured for that detector.
        ValueError: When nothing at all survives the mask.
    """
    centre = bands_calibration.centres(table)
    low, high = configs.WINDOWS[detector]

    # What the wavelength file refused to name, which is already NaN.
    columns = np.isnan(table).all(axis=1)
    blank = np.isnan(centre)
    # The sensor edges, where the window says the reading is not trusted.
    edges = ~blank & ((centre < low) | (centre > high))
    bands = blank | edges

    # Everything a value test is allowed to look at.
    live = np.ones(cube.shape, dtype=bool)
    live[:, columns, :] = False
    live[:, :, bands] = False
    if not live.any():
        raise ValueError(f"The {detector} window keeps no band of this cube.")

    # A brightness outside what light can do is not a reading.
    floor, ceiling = configs.BRIGHTNESS
    scattered = live & ((cube < floor) | (cube > ceiling) | ~np.isfinite(cube))

    # One stand-in for every refused cell, taken from what survives.
    kept = live & ~scattered
    fill = float(np.mean(cube[kept]))
    filled = np.where(kept, cube, fill).astype("f4")

    # A pixel is unusable when its column is dead or any of its bands is.
    pixels = scattered.any(axis=2)
    pixels[:, columns] = True
    return filled, Mask(columns, bands, edges, scattered, pixels, fill)

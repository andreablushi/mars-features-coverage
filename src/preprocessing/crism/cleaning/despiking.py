"""crism_ml's spike removal, run on the ratioed spectra."""

from __future__ import annotations

import numpy as np

from preprocessing.crism import configs
from preprocessing.crism.cleaning import bands_calibration
from preprocessing.crism.cleaning.destriping import medfilt1


def remove_spikes(pixspec: np.ndarray, centre: np.ndarray) -> np.ndarray:
    """Remove spikes with narrowing windows, as crism_ml does.

    Args:
        pixspec: The ratioed values as lines by samples by bands.
        centre: The centre wavelength of every band it holds.

    Returns:
        The spectra without spikes.
    """
    for width, sigma in configs.SPIKE_PASSES:
        spikes(pixspec, bands_calibration.window(centre, width), sigma)
    return pixspec


def spikes(
    pixspec: np.ndarray, size: int, sigma: float, mask: bool = False
) -> np.ndarray:
    """Replace samples further than sigma deviations from a moving median.

    Args:
        pixspec: The values to filter, changed in place.
        size: How many bands wide the median window is.
        sigma: How many deviations a sample may sit out by.
        mask: Return the flags without replacing anything.

    Returns:
        The flags, as lines by samples by bands.
    """

    def _mean(arr: np.ndarray) -> np.ndarray:
        """Mean with broadcast.

        Args:
            arr: The values to average.

        Returns:
            The mean, keeping its dimensions.
        """
        return np.mean(arr, keepdims=True)

    pixmed = medfilt1(pixspec, size)
    diff = np.abs(pixmed - pixspec)
    ind = diff > _mean(np.mean(diff, axis=-1)) + sigma * _mean(
        np.std(diff, ddof=1, axis=-1)
    )

    if not mask:
        pixspec[ind] = pixmed[ind]
    return ind

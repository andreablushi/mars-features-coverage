"""crism_ml's spike removal, run on the ratioed spectra."""

from __future__ import annotations

import numpy as np

from building.preprocessing.crism import configs
from building.preprocessing.crism.correction import bands_calibration
from building.preprocessing.crism.correction.destripe import medfilt1


def remove_spikes(pixspec: np.ndarray, centre: np.ndarray) -> np.ndarray:
    """Remove spikes with narrowing windows, as crism_ml does.

    Each pass replaces the samples sitting further than sigma deviations from a
    moving median of their own neighbours.

    Args:
        pixspec: The ratioed values as lines by samples by bands, changed in
            place.
        centre: The centre wavelength of every band it holds.

    Returns:
        The spectra without spikes.
    """
    for width, sigma in configs.SPIKE_PASSES:
        pixmed = medfilt1(pixspec, bands_calibration.window(centre, width))
        apart = np.abs(pixmed - pixspec)
        # crism_ml judges every sample against the whole cube's own spread.
        limit = np.mean(apart.mean(axis=-1), keepdims=True) + sigma * np.mean(
            apart.std(ddof=1, axis=-1), keepdims=True
        )
        caught = apart > limit
        pixspec[caught] = pixmed[caught]
    return pixspec

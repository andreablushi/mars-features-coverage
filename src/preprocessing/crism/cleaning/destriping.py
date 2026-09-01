"""crism_ml's per-column spike removal, with thresholds set for survey bands."""

from __future__ import annotations

import numpy as np

from preprocessing.crism import configs
from preprocessing.crism.fetching import bands_calibration
from preprocessing.crism.models.mask import Mask


def remove_spike_columns(
    cube: np.ndarray, mask: Mask, table: np.ndarray, detector: str
) -> tuple[np.ndarray, Mask]:
    """Replace every band of a column that spikes away from its neighbours.

    Args:
        cube: The values as lines by samples by bands, already masked.
        mask: What that masking refused.
        table: The centre wavelength of every column and band, which sets how
            many bands the smoothing window covers.
        detector: Which detector, `l` or `s`, which picks the threshold.

    Returns:
        The cube with each spiking column and band replaced by its smoothed
        value, and the mask with those recorded.
    """
    columns, bands = ~mask.columns, ~mask.bands
    block = cube[:, columns][:, :, bands]

    # Average each column down the scan, so the ground averages away.
    averaged = block.mean(axis=0)
    # How far each band sits from the median of its wavelength neighbours.
    size = window(bands_calibration.centres(table)[bands])
    apart = np.abs(averaged - medfilt1(averaged, size))
    # crism_ml judges each column against the spread of its own bands.
    sigma = configs.STRIPE_SIGMA[detector]
    limit = apart.mean(axis=-1, keepdims=True) + sigma * apart.std(
        ddof=1, axis=-1, keepdims=True
    )
    caught = apart > limit

    smoothed = medfilt1(block, size)
    levelled = cube.copy()
    inner = levelled[:, columns]
    replaced = inner[:, :, bands]
    replaced[:, caught] = smoothed[:, caught]
    inner[:, :, bands] = replaced
    levelled[:, columns] = inner

    everywhere = np.zeros(cube.shape[1:], dtype=bool)
    everywhere[np.ix_(columns, bands)] = caught
    return levelled, Mask(**{**vars(mask), "stripes": everywhere})


def medfilt1(array: np.ndarray, size: int) -> np.ndarray:
    """Return a moving median along the last axis, truncated at the ends.

    Args:
        array: The values to filter.
        size: How many samples wide the window is.

    Returns:
        The filtered values, the same shape as the input.
    """
    left, right = size // 2, size - size // 2
    return np.stack(
        [
            np.median(array[..., max(i - left, 0) : i + right], axis=-1)
            for i in range(array.shape[-1])
        ],
        axis=-1,
    )


def window(centre: np.ndarray) -> int:
    """Return how many bands the smoothing window covers at this sampling.

    Args:
        centre: The centre wavelength of every kept band, in order.

    Returns:
        An odd band count whose span stays inside `configs.STRIPE_WIDTH`, or
        three when even three bands reach further than that, since a median
        cannot be taken over fewer.
    """
    step = np.abs(np.diff(centre)).mean()
    # A window of n bands reaches across n - 1 gaps.
    size = int(configs.STRIPE_WIDTH // step) + 1
    return max(size - 1 + size % 2, 3)

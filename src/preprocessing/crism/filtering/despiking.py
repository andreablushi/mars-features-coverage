"""Replacing channels that jump away from their neighbours.

Ported from crism_ml's `preprocessing.medfilt1`, `preprocessing.spikes`,
`preprocessing.remove_spikes` and `preprocessing.remove_spikes_column`.

Differs from crism_ml:
  - Windows are given in nanometres and converted against the observation's own
    band spacing. crism_ml gives them as channel counts of 11, 7 and 3, which
    span 72, 46 and 20 nm at its 6.55 nm sampling but 398, 253 and 108 nm at the
    36 nm sampling of MSP. A mineral absorption is 50 to 200 nm wide, so the
    unconverted windows would treat real features as spikes.
  - The medians ignore NaN. `masking` leaves unusable voxels as NaN instead of
    filling them with a number, so an ordinary median would let one bad channel
    poison every window that reaches it.
  - Only the numpy moving median is kept. crism_ml prefers `bottleneck` and
    falls back to numpy; neither `bottleneck` nor `scipy` is a dependency here.
  - The cube is returned rather than filtered in place, so each step of the
    cleaning can be looked at beside the one before it.
  - Multispectral products never had the spike filter the CRISM pipeline runs
    over hyperspectral ones: their labels carry MRO:HDF_SOFTWARE_NAME as "N/A"
    where a hyperspectral label names crismhdf. This step is doing work that
    was already done upstream for everybody else.

One consequence of the conversion, seen on a real strip: at MSP's roughly 40 nm
spacing all three of crism_ml's widths land on three channels, the narrowest a
median can work over. Its shrinking passes therefore become three passes at one
width. They still refine each other, since each reads what the last left, but
the widths cannot be told apart until the sampling is finer than they are.
"""

from __future__ import annotations

import warnings

import numpy as np

from preprocessing.crism.fetching import banding


def _moving_median(array: np.ndarray, size: int) -> np.ndarray:
    """Return the moving median along the last axis, truncated at the edges.

    Args:
        array: The values to filter.
        size: The window width in channels.

    Returns:
        An array shaped like the input, holding the median of the window
        centred on each channel.
    """
    left, right = size // 2, size - size // 2
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.stack(
            [
                np.nanmedian(array[..., max(i - left, 0) : i + right], axis=-1)
                for i in range(array.shape[-1])
            ],
            axis=-1,
        )


def spikes(cube: np.ndarray, size: int, sigma: float) -> np.ndarray:
    """Return which channels sit further from the local median than they should.

    The bar is one number for the whole cube, as in crism_ml: the average
    deviation from the moving median, plus sigma times the spread of that
    deviation.

    Args:
        cube: The spectra, lines by samples by bands.
        size: The window width in channels.
        sigma: How many standard deviations a channel may stray.

    Returns:
        A boolean array shaped like the cube, true where the channel is a spike.
    """
    median = _moving_median(cube, size)
    drift = np.abs(median - cube)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        middle = np.nanmean(np.nanmean(drift, axis=-1))
        spread = np.nanmean(np.nanstd(drift, ddof=1, axis=-1))
    with np.errstate(invalid="ignore"):
        return drift > middle + sigma * spread


def remove_spikes(
    cube: np.ndarray,
    passes_nm: tuple[tuple[float, float], ...],
    spacing_nm: float,
) -> np.ndarray:
    """Replace spikes with the local median, over passes of shrinking width.

    The widest pass goes first so a broad excursion is flattened before the
    narrow passes look for single channels inside it.

    Args:
        cube: The spectra, lines by samples by bands.
        passes_nm: Each pass as its window width in nanometres and its sigma.
        spacing_nm: The gap between neighbouring band centres.

    Returns:
        A copy of the cube with the spikes replaced.
    """
    filtered = cube.astype(np.float32, copy=True)
    for width_nm, sigma in passes_nm:
        size = banding.channels(width_nm, spacing_nm)
        median = _moving_median(filtered, size)
        caught = spikes(filtered, size, sigma)
        filtered[caught] = median[caught]
    return filtered


def remove_column_spikes(
    cube: np.ndarray,
    width_nm: float,
    sigma: float,
    spacing_nm: float,
) -> np.ndarray:
    """Replace channels a whole detector column reads wrongly.

    A pushbroom column is one detector element per band, so a fault in it shows
    in every line at once. The outlier test runs on the column's average
    spectrum, and whatever it catches is replaced down the whole column.

    Args:
        cube: The spectra, lines by samples by bands.
        width_nm: The window width in nanometres.
        sigma: How many standard deviations a channel may stray.
        spacing_nm: The gap between neighbouring band centres.

    Returns:
        A copy of the cube with the faulty column channels replaced.
    """
    size = banding.channels(width_nm, spacing_nm)
    filtered = cube.astype(np.float32, copy=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        averaged = np.nanmean(filtered, axis=0)
        drift = np.abs(averaged - _moving_median(averaged, size))
        middle = np.nanmean(drift, axis=-1, keepdims=True)
        spread = np.nanstd(drift, ddof=1, axis=-1, keepdims=True)
    with np.errstate(invalid="ignore"):
        caught = drift > middle + sigma * spread
    median = _moving_median(filtered, size)
    samples, bands = caught.nonzero()
    filtered[:, samples, bands] = median[:, samples, bands]
    return filtered

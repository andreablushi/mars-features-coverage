"""Dividing each spectrum by what its own detector column usually reads.

Ported from crism_ml's `preprocessing.ratio_colmed`.

What the ratio is for: a pixel and the median of its column share the air above
them, very nearly the same illumination, and the same detector element, so
dividing one by the other cancels all three at once and leaves what makes the
pixel different from ordinary ground. It also cancels spectral smile, since a
column has one wavelength vector and both sides of the division use it.

Differs from crism_ml:
  - Only `ratio_colmed` is ported. crism_ml's `ratio()` picks its denominator
    from the blandest pixels within fifty rows, scored by a model trained on
    216 hyperspectral channels. MSP retains 38 of those, so the model cannot be
    evaluated at all.
  - Unusable pixels come out NaN rather than 0. A ratio of zero is a number a
    later step would happily average.
  - A column with nothing readable in it, which includes the four MSP never
    calibrated, comes out NaN instead of raising on an empty median.
  - The denominators are returned as well, because in this ratio they are not a
    detail: they are a spectrum of the column over the whole strip, and keeping
    them means the division can be undone or examined later.

Worth knowing before using it: a median down an MSP column is taken over the
full 2700 lines, about 566 km of ground. crism_ml's `ratio()` searches fifty
rows, about 1.8 km on a targeted image. This denominator is far less local than
the one the method was designed around.
"""

from __future__ import annotations

import warnings

import numpy as np


def colmed(
    cube: np.ndarray,
    rem: np.ndarray,
    midonly: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Ratio every spectrum against the median of its detector column.

    Args:
        cube: The spectra, lines by samples by bands.
        rem: A boolean array over lines and samples, true where the pixel is
            unusable and so is kept out of the median.
        midonly: Take the median over the middle half of the column only, which
            keeps the ends of a long strip from pulling it.

    Returns:
        The ratioed spectra, shaped like the cube, and the denominators as
        samples by bands.
    """
    ratioed = np.full(cube.shape, np.nan, dtype=np.float32)
    denominators = np.full(cube.shape[1:], np.nan, dtype=np.float32)

    for column in range(cube.shape[1]):
        readable = cube[:, column, :][~rem[:, column]]
        if midonly and len(readable) >= 4:
            edge = len(readable) // 4
            readable = readable[edge:-edge]
        if not readable.size:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            middle = np.nanmedian(readable, axis=0)
        denominators[column] = middle
        with np.errstate(divide="ignore", invalid="ignore"):
            divided = cube[:, column, :] / np.where(middle == 0, np.nan, middle)
        divided[rem[:, column]] = np.nan
        ratioed[:, column, :] = divided

    return ratioed, denominators

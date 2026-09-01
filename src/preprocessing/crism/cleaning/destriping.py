"""Levelling detector cells that read the same way off in every line."""

from __future__ import annotations

import numpy as np

from preprocessing.crism import configs
from preprocessing.crism.models.mask import Mask

# What the median absolute deviation has to be multiplied by to estimate the
# standard deviation of a normal spread.
_MAD_TO_SIGMA = 1.4826


def stripes(cube: np.ndarray, mask: Mask) -> tuple[np.ndarray, Mask]:
    """Level every column and band that sits apart from its neighbours.

    Each line of the image is read through the same grid of detector cells, so
    one cell that reads a little off reads a little off for every line, and
    paints a stripe down the whole scan in one band and one column. Averaging a
    column over every line washes the ground out, since each line saw different
    ground, and leaves what only the instrument can explain.

    A column is judged against the two beside it rather than against its own
    wavelength neighbours. Both the smile and the across track lighting vary
    smoothly from one column to the next, so a smooth profile passes, while a
    single displaced column does not. A real absorption is in every column and
    survives, which is what judging along wavelength cannot promise when the
    bands are as far apart as a multispectral survey leaves them.

    Args:
        cube: The values as lines by samples by bands, already masked.
        mask: What that masking refused, whose columns and bands say what may
            be judged and whose scattered values are left out of the averages.

    Returns:
        The cube with every stripe levelled onto its neighbours, and the mask
        with the levelled columns and bands recorded.
    """
    columns, bands = ~mask.columns, ~mask.bands
    block = cube[:, columns][:, :, bands]

    # Average each column down the scan, leaving out what was never measured.
    usable = ~mask.scattered[:, columns][:, :, bands]
    counted = usable.sum(axis=0)
    averaged = np.where(counted > 0, (block * usable).sum(axis=0) / counted, np.nan)

    # How far each column falls from the line drawn through the two beside it.
    apart = np.full(averaged.shape, np.nan)
    apart[1:-1] = averaged[1:-1] - 0.5 * (averaged[:-2] + averaged[2:])
    # The curvature this band carries anyway, measured so outliers cannot
    # inflate it, which a standard deviation over the same values would.
    middle = np.nanmedian(apart, axis=0)
    spread = _MAD_TO_SIGMA * np.nanmedian(np.abs(apart - middle), axis=0)

    # A stripe stands out from its own band's curvature, not from a fixed size.
    limit = configs.STRIPE_SIGMA * spread
    found = np.abs(apart) > np.where(spread > 0, limit, np.inf)

    # Subtract the offset rather than overwrite, so the ground down the column
    # is kept and only what the cell adds to every line is taken away.
    levelled = cube.copy()
    inner = levelled[:, columns]
    corrected = inner[:, :, bands]
    corrected[:, found] -= apart[found].astype(corrected.dtype)
    inner[:, :, bands] = corrected
    levelled[:, columns] = inner

    # Say where that happened, on the full grid rather than the kept block.
    everywhere = np.zeros(cube.shape[1:], dtype=bool)
    everywhere[np.ix_(columns, bands)] = np.nan_to_num(found)
    return levelled, Mask(**{**vars(mask), "stripes": everywhere})

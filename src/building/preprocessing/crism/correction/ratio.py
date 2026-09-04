"""Dividing each spectrum by a bland one from its own column."""

from __future__ import annotations

import numpy as np


def ratio_colmed(pixspec: np.ndarray, rem: np.ndarray) -> np.ndarray:
    """Use the median of a column for ratioing, as crism_ml's ColMed does.

    Args:
        pixspec: The values as lines by samples by bands.
        rem: Lines by samples, True where the pixel is not a measurement and so
            is kept out of the median.

    Returns:
        The ratioed spectra, with the refused pixels set to zero.
    """

    def medcol(idx: int) -> np.ndarray:
        """Ratio one column against the median of its own usable spectra.

        Args:
            idx: Which sample across the slit.

        Returns:
            That column's spectra, divided through.
        """
        column = pixspec[:, idx, :]
        live = ~rem[:, idx]
        normed = np.zeros_like(column)
        # A column holding no measurement at all has nothing to ratio against,
        # and every spectrum of it is refused anyway.
        if live.any():
            normed[live] = column[live] / np.median(column[live], axis=0)
        return normed

    return np.stack([medcol(i) for i in range(pixspec.shape[1])], axis=1)

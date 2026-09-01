"""The centre wavelength of every detector column and band, as a file gives it."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from preprocessing.pds import images, labels

# What a wavelength file writes where the detector was never calibrated.
UNCALIBRATED = 65535.0


def load(image: Path) -> np.ndarray:
    """Read the centre wavelengths one wavelength file holds.

    Args:
        image: The file's `.img`, whose `.lbl` sits beside it and says how it
            is shaped.

    Returns:
        The centre wavelength in nm of every column and band, as columns by
        bands, in the band order the file stores. Columns and bands the
        detector was never calibrated for hold NaN.

    Raises:
        FileNotFoundError: When the file or its label is missing.
        ValueError: When the label names a band order this cannot read.
        KeyError: When it names a sample type this cannot read.
    """
    label = labels.load(image.with_suffix(".lbl"))
    # A wavelength file holds one line, so its cube is one grid deep.
    table = images.build_cube(image, label)[0]
    # Say what was never calibrated with NaN rather than a number.
    return np.where(table >= UNCALIBRATED, np.nan, table.astype("f8"))

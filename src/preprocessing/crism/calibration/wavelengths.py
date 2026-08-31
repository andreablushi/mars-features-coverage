"""The centre wavelength of every detector column and band, per mode."""

from __future__ import annotations

from pathlib import Path

import numpy as np

# Where the calibration records are kept.
_WA_PATH = Path(__file__).parent / "cdr"

# Which record holds one detector's wavelengths
_TABLES = {
    ("l", 55): ("infrared_55.img", 55, 0),
    ("l", 70): ("infrared_70.img", 70, 0),
    ("s", 18): ("visible_19.img", 19, 1),
    ("s", 19): ("visible_19.img", 19, 0),
    ("s", 24): ("visible_25.img", 25, 1),
    ("s", 25): ("visible_25.img", 25, 0),
}

# How many detector columns a multispectral survey scan is binned to.
COLUMNS = 64

# What a calibration record writes where the detector was never calibrated.
UNCALIBRATED = 65535.0


def load(detector: str, bands: int) -> np.ndarray:
    """Read the centre wavelengths of one detector at one band count.

    Args:
        detector: Which detector, `l` for infrared or `s` for visible.
        bands: How many bands the observation holds, which is what decides
            which record applies and where in it to start.

    Returns:
        The centre wavelength in nm of every column and band, as columns by
        bands, in the band order the record stores. Columns and bands the
        detector was never calibrated for hold NaN.

    Raises:
        KeyError: When no record covers that detector at that band count.
    """
    # The record covering this detector, what it holds, and where to start.
    name, stored, skip = _TABLES[detector, bands]
    raw = (_WA_PATH / name).read_bytes()
    # It is written line interleaved, so bands sit between line and column.
    grid = np.frombuffer(raw, dtype="<f4", count=COLUMNS * stored)
    table = grid.reshape(stored, COLUMNS).T.astype("f8")[:, skip:]
    # Say what was never calibrated with NaN rather than a number.
    return np.where(table >= UNCALIBRATED, np.nan, table)

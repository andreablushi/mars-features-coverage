"""Reading the image a PDS label describes, whatever the product is."""

from __future__ import annotations

from pathlib import Path

import numpy as np

# What a PDS sample type and width mean as a numpy dtype.
_DTYPES = {
    ("PC_REAL", 32): "<f4",
    ("PC_REAL", 64): "<f8",
    ("MSB_INTEGER", 16): ">i2",
    ("UNSIGNED_INTEGER", 8): "u1",
}

# The two orders an image is written in.
_BIL = "LINE_INTERLEAVED"
_BSQ = "BAND_SEQUENTIAL"


def build_cube(image: Path, label: dict[str, str]) -> np.ndarray:
    """Read one image into an array indexed by line, sample and band.

    Args:
        image: The `.img` file holding the values.
        label: The parsed label describing it.

    Returns:
        The values as lines by samples by bands, in the band order the file
        stores them in.

    Raises:
        ValueError: When the label names a band order this cannot read.
        KeyError: When it names a sample type this cannot read.
    """
    # How the image is shaped, ordered and written.
    lines, samples, bands, stored, dtype = load_layout(label)
    # How many values the cube holds, the trailing record excluded.
    wanted = lines * samples * bands
    # Read exactly those, so any table written after them is left alone.
    flat = np.fromfile(image, dtype=dtype, count=wanted)
    # BIL writes one line's bands together, so bands sit in the middle.
    if stored == _BIL:
        return flat.reshape(lines, bands, samples).transpose(0, 2, 1)
    # BSQ writes whole bands one after another, so bands come first.
    return flat.reshape(bands, lines, samples).transpose(1, 2, 0)


def load_layout(label: dict[str, str]) -> tuple[int, int, int, str, str]:
    """Read how one image is shaped and written from its label.

    Args:
        label: The parsed label.

    Returns:
        The lines, samples and bands it holds, the order its bands are written
        in, and the numpy dtype its samples are stored as.

    Raises:
        ValueError: When the label names a band order this cannot read.
        KeyError: When it names a sample type this cannot read.
    """
    # How many rows the image holds.
    lines = int(label["LINES"])
    # How many columns each row holds.
    samples = int(label["LINE_SAMPLES"])
    # How many channels each pixel holds, which a single band image omits.
    bands = int(label.get("BANDS", 1))
    # The order bands are written in, BIL for a TRDR and BSQ for a DDR.
    stored = label.get("BAND_STORAGE_TYPE", _BIL)
    if stored not in (_BIL, _BSQ):
        raise ValueError(f"Cannot read a {stored} image.")
    # The sample type and its width, which together name a numpy dtype.
    dtype = _DTYPES[label["SAMPLE_TYPE"], int(label["SAMPLE_BITS"])]
    return lines, samples, bands, stored, dtype

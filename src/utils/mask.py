"""How a footprint's cells are packed, written once and read back."""

from __future__ import annotations

import numpy as np

DENSE = 0
SPARSE = 1

_INDEX = np.dtype("<u4")


def encode(filled: np.ndarray) -> bytes:
    """Pack the cells a footprint fills into whichever form is smaller.

    Args:
        filled: One flag per cell, row by row, flattened.

    Returns:
        The tag byte followed by the packed cells.
    """
    cells = np.flatnonzero(filled).astype(_INDEX)
    if cells.nbytes < (filled.size + 7) // 8:
        return bytes([SPARSE]) + cells.tobytes()
    return bytes([DENSE]) + np.packbits(filled).tobytes()


def cells_of(mask: bytes) -> np.ndarray:
    """Return the cells one packed footprint fills.

    Args:
        mask: One footprint's mask, as encode wrote it.

    Returns:
        The indices of the filled cells, in ascending order.
    """
    if mask[0] == SPARSE:
        return np.frombuffer(mask, dtype=_INDEX, offset=1)
    bits = np.unpackbits(np.frombuffer(mask, dtype=np.uint8, offset=1))
    return np.flatnonzero(bits).astype(_INDEX)

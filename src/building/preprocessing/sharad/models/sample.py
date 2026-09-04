"""One SHARAD radargram with its geometry joined onto it."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SharadSample:
    """One track holding only the traces its geometry places.

    Attributes:
        identifier: The observation id.
        power: Delay samples by traces, holding only the placed traces.
        geometry: One row per kept trace, in the same order.
        traces: Which of the original radargram columns these traces are,
            counted from zero.
    """

    identifier: str
    power: np.ndarray
    geometry: np.recarray
    traces: np.ndarray

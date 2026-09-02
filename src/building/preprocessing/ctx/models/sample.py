"""One CTX scan placed on its grid."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CtxSample:
    """One scan with its grid checked against the corners its label claims.

    Attributes:
        identifier: The observation id.
        image: The brightness as lines by samples.
        blank: Lines by samples, True where the projection left no ground,
            which is every pixel outside the corners the scan swept.
        latitude: The centre latitude in degrees of every line.
        longitude: The centre longitude in degrees of every sample.
        pixel: How many degrees one pixel spans, the same in both directions.
    """

    identifier: str
    image: np.ndarray
    blank: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    pixel: float

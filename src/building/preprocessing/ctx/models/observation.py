"""One CTX scan as it comes off disk, raw and whole."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CtxObservation:
    """One projected scan with the grid its label places it on.

    Attributes:
        identifier: The observation id, such as P01_001393_1655_XN_14S149W.
        image: The brightness as lines by samples, as ASU stretched it, with
            zero standing for the ground the projection left blank.
        label: The parsed ISIS label, whose Mapping group places the grid.
        latitude: The centre latitude in degrees of every line.
        longitude: The centre longitude in degrees of every sample.
    """

    identifier: str
    image: np.ndarray
    label: dict[str, str]
    latitude: np.ndarray
    longitude: np.ndarray

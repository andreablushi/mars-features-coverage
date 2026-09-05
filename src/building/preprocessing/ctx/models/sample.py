"""One CTX scan placed on its grid."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# What the projection writes where the scan swept no ground.
BLANK = 0


@dataclass(frozen=True, slots=True)
class CtxSample:
    """One scan with its grid checked against the corners its label claims.

    Attributes:
        identifier: The observation id.
        image: The brightness as lines by samples.
        latitude: The centre latitude in degrees of every line.
        longitude: The centre longitude in degrees of every sample.
        pixel: How many degrees one pixel spans, the same in both directions.
    """

    identifier: str
    image: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    pixel: float

    # An RDR is projected onto a regular grid, so one axis places each side.
    separable = True

    @property
    def blank(self) -> np.ndarray:
        """Return where the projection left no ground.

        Returns:
            Lines by samples, True at every pixel outside the corners the scan
            swept, worked out from the image rather than carried beside it.
        """
        return self.image == BLANK

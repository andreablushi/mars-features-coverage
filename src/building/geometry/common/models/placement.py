"""Where every sample of one observation sits, relative to its own feature."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Placement:
    """Where each sample of one observation sits on the feature it was kept for.

    The offsets are degrees from the feature's own centre and never absolute
    coordinates, so a placement says how an observation sits on its feature and
    never where that feature is on Mars. Degrees rather than metres is what
    keeps a regular map raster to one axis each: its grid is regular in degrees
    and curved in any metric projection, so metres are worked out on demand by
    `project.metres` and are never the thing stored.

    Attributes:
        north: Degrees north of the feature centre. One per line where the grid
            is separable, and one per sample where it is not.
        east: Degrees east of it, wrapped so the meridian is no jump. One per
            sample of a line where the grid is separable, and otherwise shaped
            as `north` is.
        separable: Whether the two hold one axis each, a line's north and a
            sample's east, rather than a value for every sample.
    """

    north: np.ndarray
    east: np.ndarray
    separable: bool

    @property
    def ground_axes(self) -> int:
        """Return how many axes of ground the placement places.

        Returns:
            The two a separable grid crosses, and otherwise the axes the
            offsets are already held over.
        """
        return 2 if self.separable else self.north.ndim

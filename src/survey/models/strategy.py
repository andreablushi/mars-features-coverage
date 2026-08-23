"""What a window has to hold from each instrument before it is worth keeping."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

Floors = list[tuple[tuple[int, ...], float]]


@dataclass(frozen=True, slots=True)
class Strategy:
    """One way of asking the instruments for what only they can give.

    An imager sweeps a swath and a sounder draws a line, so asking both for
    the same share of the ground asks one for everything it has and the other
    for what it cannot do. Each strategy therefore names its own demand per
    instrument, and the sounder is named by every one of them, since a feature
    with no subsurface is not what this dataset is for.

    Attributes:
        name: What the strategy is called, which is how a run picks it and how
            one comparison is told from another.
        demands: The share of the ground each instrument the strategy insists
            on has to reach inside a window, by instrument id. An instrument it
            does not name is welcome in a window but never asked for.
    """

    name: str
    demands: dict[str, float]

    def floors(self, iids: Sequence[str], area_km2: float) -> Floors | None:
        """Work out how much ground each instrument insisted on has to reach.

        Args:
            iids: The instrument each set on the timeline belongs to, in the
                order the timeline indexes them.
            area_km2: How much ground the search is run over.

        Returns:
            The sets that can answer for one instrument and the ground any one
            of them has to reach, one entry per instrument insisted on, or None
            when the record holds no set at all for one of them.
        """
        floors: Floors = []
        for iid, share in self.demands.items():
            answering = tuple(index for index, owner in enumerate(iids) if owner == iid)
            if not answering:
                return None
            floors.append((answering, share * area_km2))
        return floors

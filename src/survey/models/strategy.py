"""What a window has to hold from each instrument before it is worth keeping."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Demands = list[tuple[tuple[int, ...], int]]


@dataclass(frozen=True, slots=True)
class Strategy:
    """One way of asking the instruments for what only they can give.

    Attributes:
        name: What the strategy is called, which is how a run picks it and how
            one comparison is told from another.
        demands: The share of the tile each instrument the strategy insists on
            has to reach inside a window, by instrument id. An instrument it
            does not name is welcome in a window but never asked for.
        crossing_km: How far a sounder's line has to run inside a tile before
            it is a look at the tile rather than a clip of its edge. A line is
            asked for a length rather than a share of the ground, since a swath
            a few kilometres wide cannot fill a tile however far it runs.
    """

    name: str
    demands: dict[str, float]
    crossing_km: float

    def floors(
        self, iids: Sequence[str], area_km2: float, cell_km2: float
    ) -> Demands | None:
        """Work out how much ground each instrument insisted on has to reach.

        Args:
            iids: The instrument each set on the timeline belongs to, in the
                order the timeline indexes them.
            area_km2: How much ground the search is run over.
            cell_km2: How much ground one cell of that ground covers.

        Returns:
            The sets that can answer for one instrument and the cells any one
            of them has to reach, one entry per instrument insisted on and the
            tightest demand first so that a window fails on it soonest, or None
            when the record holds no set at all for one of them.
        """
        floors: Demands = []
        for iid, share in self.demands.items():
            answering = tuple(index for index, owner in enumerate(iids) if owner == iid)
            if not answering:
                return None
            floors.append((answering, max(1, math.ceil(share * area_km2 / cell_km2))))
        return sorted(floors, key=lambda demand: -demand[1])

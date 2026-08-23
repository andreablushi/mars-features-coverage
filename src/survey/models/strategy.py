"""What a window has to hold from each instrument before it is worth keeping."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Demands = list[tuple[tuple[int, ...], int]]


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
        demands: The share of the tile each instrument the strategy insists on
            has to reach inside a window, by instrument id. An instrument it
            does not name is welcome in a window but never asked for.
    """

    name: str
    demands: dict[str, float]

    def floors(
        self, iids: Sequence[str], area_km2: float, cell_km2: float
    ) -> Demands | None:
        """Work out how much ground each instrument insisted on has to reach.

        The ground is read back as a count of the tile's cells, which is the
        same ground said in the unit the sweep counts in: every cell of a
        feature covers the same area, so a share of the tile is a share of its
        cells. A demand of nothing still asks for one cell, since an
        instrument that reached none of the tile was never there.

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

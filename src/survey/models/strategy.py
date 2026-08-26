"""What a window has to hold from each instrument before it is worth keeping."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# One instrument answering a demand: the sets that speak for it and its floor
Answer = tuple[tuple[int, ...], int]
# A demand any one of its instruments can answer, and what a window is asked.
Demands = list[list[Answer]]


@dataclass(frozen=True, slots=True)
class Strategy:
    """One way of asking the instruments for what only they can give.

    Attributes:
        name: What the strategy is called, which is how a run picks it.
        demands: The demands a window meets all of, any one instrument answering each.
        admits: The pixels each instrument has to land on a whole tile to count, by iid.
        tile_km: The widest a tile of a feature may be, in kilometres.
        gain: The cells an observation has to bring, or it is dropped as a repeat.
        breadth: What a window gains for each extra instrument answering one demand.
        span_days: How long a window may run, in days.
        timeless: The instruments the ground answers for whenever they came.
    """

    name: str
    demands: tuple[dict[str, float], ...]
    admits: dict[str, float]
    tile_km: float
    gain: int
    breadth: float
    span_days: float
    timeless: frozenset[str] = frozenset()

    def floors(
        self, iids: Sequence[str], area_km2: float, cell_km2: float
    ) -> tuple[Demands, Demands]:
        """Work out how much ground each instrument insisted on has to reach.

        Args:
            iids: The instrument each set on the timeline belongs to, in order.
            area_km2: How much ground the search is run over.
            cell_km2: How much ground one cell of that ground covers.

        Returns:
            What a window is scored on and what the record answers for, tightest first.
        """
        windowed: Demands = []
        standing: Demands = []
        for demand in self.demands:
            answers = [
                (
                    tuple(index for index, owner in enumerate(iids) if owner == iid),
                    max(1, math.ceil(share * area_km2 / cell_km2)),
                )
                for iid, share in demand.items()
            ]
            # A demand is out of the window only when everything answering it is
            held = standing if all(iid in self.timeless for iid in demand) else windowed
            held.append(answers)
        return (
            sorted(windowed, key=_tightest),
            sorted(standing, key=_tightest),
        )


def _tightest(answers: list[Answer]) -> int:
    """Say how soon a window fails one demand, so the soonest is tried first.

    Args:
        answers: The instruments that can answer the demand, and their floors.

    Returns:
        The least it can answer with, negated so the hardest demand sorts first.
    """
    return -min(floor for _, floor in answers)

"""What a window has to hold from each instrument before it is worth keeping."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# One instrument that can answer a demand: the sets that speak for it, and the
# cells any one of them has to reach.
Answer = tuple[tuple[int, ...], int]
# A demand any one of its instruments can answer, and what a window is asked.
Demands = list[list[Answer]]


@dataclass(frozen=True, slots=True)
class Strategy:
    """One way of asking the instruments for what only they can give.

    Attributes:
        name: What the strategy is called, which is how a run picks it and how
            one comparison is told from another.
        demands: What a window is asked for, as a run of demands it has to
            meet all of. One demand names the instruments that can answer it
            and the share of the tile each of them has to reach, so any one of
            them answering meets it. An instrument named nowhere is welcome in
            a window but never asked for.
        admits: The pixels each instrument has to land on a whole tile before
            it counts as a look at it rather than a clip of its edge, by
            instrument id. A tile holding less of the feature is asked less of
            it. The instruments differ by orders of magnitude here, since an
            imager lays down millions of pixels where a sounder lays down
            tens. An instrument named nowhere is asked for nothing, so it has
            only to reach the tile.
        tile_km: How wide a tile of a feature is, in kilometres, which is
            what a window is searched over one of. The cells were sized by the
            run that measured the feature, so a tile is cut to the nearest
            whole number of them.
        gain: The cells an observation has to bring a window that no other
            observation of its own set already reaches, or it is dropped from
            the window as a repeat of ground the window already holds. Raising
            it thins a window down to the observations that really add ground,
            and lowering it keeps every look that brought anything at all.
        breadth: How much a window is worth for each extra instrument
            answering the same demand. Any one of a demand's instruments meets
            it, so without this the search has no reason to reach for the
            others. The higher it is, the longer a window the search will
            accept in order to gather more of them over the same ground, and
            at nought it stops reaching for them at all.
        span_days: How long a window may run. A Mars year is every season the
            ground has, but a surface reading holds far longer than that, so
            what the span should be is one of the things a comparison settles.
        timeless: The instruments the ground answers for whenever they came,
            rather than inside the window. What a sounder reads is the rock
            under the ground, which does not turn with the seasons, so asking
            its track to be contemporary with an image buys nothing and
            stretches the window to the next time it flew over.
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
            iids: The instrument each set on the timeline belongs to, in the
                order the timeline indexes them.
            area_km2: How much ground the search is run over.
            cell_km2: How much ground one cell of that ground covers.

        Returns:
            What a window is scored on and what the whole record answers for,
            each holding one entry per demand, and in it the sets that can
            answer for each instrument and the cells any one of them has to
            reach. The tightest demand comes first so that a window fails on it
            soonest. Every demand is mandatory, so an instrument no set answers
            for is left with nothing answering for it and cannot answer.
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
        answers: The instruments that can answer the demand, and the cells any
            one of them has to reach.

    Returns:
        The least a window can reach and still answer it, negated so that the
        hardest demand sorts first.
    """
    return -min(floor for _, floor in answers)

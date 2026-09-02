"""What a window has to hold from each instrument before it is worth keeping."""

from __future__ import annotations

from dataclasses import dataclass, field

# One instrument answering a constraint: the sets that speak for it and its floor
Answer = tuple[tuple[int, ...], int]
# A constraint any one of its instruments can answer, and what a window is asked.
Constraints = list[list[Answer]]


@dataclass(frozen=True, slots=True)
class Strategy:
    """One way of asking the instruments for what only they can give.

    Attributes:
        name: What the strategy is called, which is how a run picks it.
        constraints: What a window meets all of, any one instrument answering each.
        admits: The pixels each instrument has to land on a whole tile to count, by iid.
        tile_km: The widest a tile of a feature may be, in kilometres.
        span_days: How long a window may run, in days.
        timeless: The instruments the ground answers for whenever they came.
        least: The pixels each set has to land on each tile, by tile then set.
        windowed: What a window is scored on, by tile, tightest constraint first.
        standing: What the whole record answers for, by tile, tightest first.
    """

    name: str
    constraints: tuple[dict[str, float], ...]
    admits: dict[str, float]
    tile_km: float
    span_days: float
    timeless: frozenset[str] = frozenset()
    least: list[list[float]] = field(default_factory=list)
    windowed: list[Constraints] = field(default_factory=list)
    standing: list[Constraints] = field(default_factory=list)

"""What a window has to hold from each instrument before it is worth keeping."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Strategy:
    """One way of asking the instruments for what only they can give.

    Attributes:
        name: What the strategy is called, which is how a run picks it.
        constraints: What a window meets all of, any one instrument answering each.
        admits: The pixels each instrument has to land on a whole tile to count, by iid.
        tile_km: The widest a tile of a feature may be, in kilometres.
        gain: The cells an observation has to bring, or it is dropped as a repeat.
        span_days: How long a window may run, in days.
        timeless: The instruments the ground answers for whenever they came.
    """

    name: str
    constraints: tuple[dict[str, float], ...]
    admits: dict[str, float]
    tile_km: float
    gain: int
    span_days: float
    timeless: frozenset[str] = frozenset()

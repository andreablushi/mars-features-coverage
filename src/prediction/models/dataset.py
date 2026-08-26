"""What one strategy would make of every feature searched."""

from __future__ import annotations

from dataclasses import dataclass

from prediction.models.aggregate import Aggregate
from prediction.models.spread import Spread


@dataclass(frozen=True, slots=True)
class DatasetStats:
    """What one strategy would make of every feature searched.

    Attributes:
        strategy: The strategy the features were searched under.
        features: How many features were searched.
        held: Every tile of every feature, read as one.
        sizes: How much ground a tile holds, over the tiles searched.
        offered: How many observations each instrument landed on a tile searched.
        overlap: The share of a tile every instrument reaches at once, over the kept.
        iids: The instruments reported on, in the order they are drawn.
    """

    strategy: str
    features: int
    held: Aggregate
    sizes: Spread
    offered: dict[str, Spread]
    overlap: Spread
    iids: list[str]

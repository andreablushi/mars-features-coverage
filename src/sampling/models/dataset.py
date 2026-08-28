"""What one strategy would make of every feature searched."""

from __future__ import annotations

from dataclasses import dataclass

from sampling.models.aggregate import Aggregate
from sampling.models.spread import Spread


@dataclass(frozen=True, slots=True)
class ClassStats:
    """What one strategy would make of the features of one class.

    Attributes:
        selected: How many features of the class earned a window on any tile.
        covered: The share of a selected feature the dataset would hold, as the
            mean over its tiles of the ground any instrument reaches on one, so
            a tile that earned no window counts as nothing. Read feature by
            feature, so the spread is how much the features of the class differ.
        days: How long a window runs on a kept tile, feature by feature.
    """

    selected: int
    covered: Spread
    days: Spread


@dataclass(frozen=True, slots=True)
class DatasetStats:
    """What one strategy would make of every feature searched.

    Attributes:
        strategy: The strategy the features were searched under.
        features: How many features were searched.
        classes: What it made of each feature class, by class.
        held: Every tile of every feature, read as one.
        widths: How wide a tile is, as the side of a square holding the feature
            ground it covers, in kilometres, over the tiles searched.
        offered: How many observations each instrument landed on a tile searched.
        overlap: The share of a tile every instrument reaches at once, over the kept.
        iids: The instruments reported on, in the order they are drawn.
    """

    strategy: str
    features: int
    classes: dict[str, ClassStats]
    held: Aggregate
    widths: Spread
    offered: dict[str, Spread]
    overlap: Spread
    iids: list[str]

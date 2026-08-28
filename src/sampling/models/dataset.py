"""What one strategy would make of every feature searched."""

from __future__ import annotations

from dataclasses import dataclass

from sampling.models.spread import Spread
from sampling.models.tiles import Aggregate, TileStats


@dataclass(frozen=True, slots=True)
class SearchedFeature:
    """What searching every tile of one feature under one strategy left.

    Attributes:
        strategy: The strategy it was searched under.
        feature_class: The class the catalogue files the feature under.
        iids: The instruments it holds, in the order they are drawn.
        tiles: The tiles the search ran over, as it left them.
    """

    strategy: str
    feature_class: str
    iids: list[str]
    tiles: list[TileStats]


@dataclass(frozen=True, slots=True)
class ClassStats:
    """What one strategy would make of the features of one class.

    Attributes:
        selected: How many features of the class earned a window on any tile.
        covered: The share of a selected feature each instrument would reach, by
            instrument, as the mean over the feature's tiles of the ground it
            reaches on one, so a tile that earned no window counts as nothing.
            Read feature by feature, so the spread is how much the features of
            the class differ.
        taken: How many observations of a selected feature each instrument
            keeps, by instrument, added over the feature's kept tiles so an
            observation serving two of them counts once for each. Read feature
            by feature, like the rest.
        days: How long a window runs on a kept tile, feature by feature.
    """

    selected: int
    covered: dict[str, Spread]
    taken: dict[str, Spread]
    days: Spread


@dataclass(frozen=True, slots=True)
class DatasetStats:
    """What one strategy would make of every feature searched.

    Attributes:
        strategy: The strategy the features were searched under.
        features: How many features were searched.
        classes: What it made of each feature class, by class.
        tiles: Every tile of every feature, read as one.
        widths: How wide a tile is, as the side of a square holding the feature
            ground it covers, in kilometres, over the tiles searched.
        offered: How many observations each instrument landed on a tile searched.
        overlap: The share of a tile every instrument reaches at once, over the kept.
        iids: The instruments reported on, in the order they are drawn.
    """

    strategy: str
    features: int
    classes: dict[str, ClassStats]
    tiles: Aggregate
    widths: Spread
    offered: dict[str, Spread]
    overlap: Spread
    iids: list[str]

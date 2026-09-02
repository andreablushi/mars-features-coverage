"""What the filter would make of every feature searched."""

from __future__ import annotations

from dataclasses import dataclass

from analysis.sampling.models.feature import Aggregate, FeatureStats
from analysis.sampling.models.spread import Spread


@dataclass(frozen=True, slots=True)
class SearchedFeature:
    """What searching one feature under the filter left.

    Attributes:
        feature_class: The class the catalogue files the feature under.
        iids: The instruments it holds, in the order they are drawn.
        stats: What the search left on it, or None where it held nothing to search.
    """

    feature_class: str
    iids: list[str]
    stats: FeatureStats | None


@dataclass(frozen=True, slots=True)
class ClassStats:
    """What the filter would make of the features of one class.

    Attributes:
        selected: How many features of the class earned a window.
        taken: How many observations of a selected feature each instrument
            keeps, by instrument. Read feature by feature, so the spread is how
            much the features of the class differ.
    """

    selected: int
    taken: dict[str, Spread]


@dataclass(frozen=True, slots=True)
class DatasetStats:
    """What the filter would make of every feature searched.

    Attributes:
        features: How many features were searched.
        classes: What it made of each feature class, by class.
        held: Every feature searched, read as one.
        widths: How wide a feature is, as the side of a square holding the ground
            it covers, in kilometres, over the features searched.
        offered: How many observations each instrument landed on a feature searched.
        overlap: The share of a feature every instrument reaches at once, over the kept.
        iids: The instruments reported on, in the order they are drawn.
    """

    features: int
    classes: dict[str, ClassStats]
    held: Aggregate
    widths: Spread
    offered: dict[str, Spread]
    overlap: Spread
    iids: list[str]

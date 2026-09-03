"""What the filter left of every feature the selection searched, read as one."""

from __future__ import annotations

from dataclasses import dataclass

from analysis.stats.models.spread import Spread


@dataclass(frozen=True, slots=True)
class Aggregate:
    """What a run of features holds between them.

    Attributes:
        searched: How many features the search ran over.
        kept: How many of them earned a window worth keeping.
        area_km2: How much ground those searched features hold.
        days: How long the windows last, over the kept features.
        geo_mean: The geometric mean its window scores, over the kept features.
        reached: The share of a feature each instrument reaches, over the kept.
        landed: The pixels each instrument landed on a feature, over the kept.
        pixels_per_look: The pixels one observation of each instrument landed on
            a feature, over the kept features it took any of.
        pixel_km2: The ground one pixel of each instrument covers, over every
            feature searched, since an instrument's pixel is the same size
            whichever feature it falls on and whether or not it earned a window.
        overlaps: The ground each set of instruments reaches, most ground first.
    """

    searched: int
    kept: int
    area_km2: float
    days: Spread
    geo_mean: Spread
    reached: dict[str, Spread]
    landed: dict[str, Spread]
    pixels_per_look: dict[str, Spread]
    pixel_km2: dict[str, Spread]
    overlaps: dict[tuple[str, ...], float]


@dataclass(frozen=True, slots=True)
class ClassStats:
    """What the filter left of the features of one class.

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
    """What the filter left of every feature searched.

    Attributes:
        features: How many features were searched.
        classes: What it left of each feature class, by class.
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

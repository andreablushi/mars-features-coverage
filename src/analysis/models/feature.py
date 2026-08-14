"""The feature a coverage measurement is made against."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeatureBox:
    """The bounding box coverage is measured against.

    Attributes:
        name: The feature name as ODE spells it.
        feature_class: The feature class, such as Crater or Collis.
        min_lat: The southernmost latitude in degrees.
        max_lat: The northernmost latitude in degrees.
        west_lon: The westernmost longitude in degrees.
        east_lon: The easternmost longitude in degrees.
    """

    name: str
    feature_class: str
    min_lat: float
    max_lat: float
    west_lon: float
    east_lon: float

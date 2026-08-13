"""Everything one feature contributes to a coverage computation."""

from __future__ import annotations

from dataclasses import dataclass

from analysis.models.feature import FeatureBox
from analysis.models.observation import Observation


@dataclass(frozen=True, slots=True)
class FeatureData:
    """One feature's box together with its observations.

    Attributes:
        box: The bounding box coverage is measured against.
        observations: The observations, in chronological order across every
            instrument set.
    """

    box: FeatureBox
    observations: list[Observation]

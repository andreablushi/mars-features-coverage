"""One feature read across every tile the search ran over it."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from prediction.models.aggregate import Aggregate
from prediction.models.tiles import TileStats
from prediction.stats import aggregate, tiles
from survey.models.study import Study


@dataclass(frozen=True, slots=True)
class FeatureStats:
    """What one feature holds, tile by tile and across all of them.

    Attributes:
        held: The tiles read as one.
        tiles: How many tiles hold any of the feature.
        across: How many tiles the feature was cut into along each axis.
        feature_km2: How much ground the feature's bounding box covers.
        iids: The instruments reported on, in the order they are drawn.
    """

    held: Aggregate
    tiles: int
    across: int
    feature_km2: float
    iids: list[str]


def read(
    study: Study, measured: Sequence[TileStats], feature_km2: float
) -> FeatureStats:
    """Read one feature across the tiles the search ran over.

    Args:
        study: What the search found over it.
        measured: Those tiles, as the search left them.
        feature_km2: How much ground its bounding box covers.

    Returns:
        The feature.
    """
    iids = tiles.instruments(study)
    return FeatureStats(
        held=aggregate.over(measured, iids),
        tiles=study.tiles,
        across=study.patchwork.across,
        feature_km2=feature_km2,
        iids=iids,
    )

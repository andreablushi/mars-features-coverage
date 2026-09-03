"""Laying one catalogued feature's grid back onto the mosaic."""

from __future__ import annotations

from functools import lru_cache

from analysis.metadata.loaders.features import load_features
from analysis.models.feature import Feature
from analysis.visualization.feature.models.placing import Placed
from utils.disk.slugify import slugify

HALF_TURN_DEG = 180.0


def placed(feature_class: str, name: str, side: int) -> Placed | None:
    """Lay one feature's grid back onto the mosaic."""
    grid = Placed(_catalogue()[slugify(feature_class), slugify(name)], side)
    # A feature wrapping the planet has no lon/lat box a plate carree crop can cover
    lon, _ = grid.outline()
    return grid if lon.max() - lon.min() <= HALF_TURN_DEG else None


@lru_cache(maxsize=1)
def _catalogue() -> dict[tuple[str, str], Feature]:
    """Read the feature catalogue once, keyed by the slugs the trees use."""
    return {
        (slugify(feature.feature_class), slugify(feature.name)): feature
        for feature in load_features()
    }

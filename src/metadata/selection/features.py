"""Feature selection: filter the catalog and give a point feature a size."""

from __future__ import annotations

from collections.abc import Sequence

from metadata import configs
from models.feature import Feature


def select_features(features: Sequence[Feature]) -> tuple[list[Feature], list[Feature]]:
    """Size the point features of the catalog and set aside the sizeless ones.

    Args:
        features: The full feature catalog.

    Returns:
        The usable features, and the sizeless ones left unqueried for want of an extent.
    """
    usable: list[Feature] = []
    sizeless: list[Feature] = []
    for feature in features:
        if not feature.is_point:
            usable.append(feature)
        elif feature.feature_class in configs.SIZED_POINT_CLASSES:
            usable.append(feature.enlarged(configs.POINT_RADIUS_DEG))
        else:
            sizeless.append(feature)
    return usable, sizeless

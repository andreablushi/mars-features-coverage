"""Feature selection: filter the catalog and give a point feature a size."""

from __future__ import annotations

from collections.abc import Sequence

from download import configs
from models.feature import Feature


def select_features(
    features: Sequence[Feature], *, names: Sequence[str] | None = None
) -> tuple[list[Feature], list[Feature]]:
    """Filter the catalog to the requested features and size the point ones.

    Args:
        features: The full feature catalog.
        names: Optional feature names to keep.

    Returns:
        The usable features, and the sizeless ones left unqueried for want of an extent.
    """
    # Format the requested names into a set
    wanted = {name.strip().lower() for name in names} if names else None

    # Filter the catalog to the requested features, preserving its own spelling
    selected = [
        feature
        for feature in features
        if wanted is None or feature.name.lower() in wanted
    ]

    usable: list[Feature] = []
    sizeless: list[Feature] = []
    for feature in selected:
        if not feature.is_point:
            usable.append(feature)
        elif feature.feature_class in configs.SIZED_POINT_CLASSES:
            usable.append(feature.enlarged(configs.POINT_RADIUS_DEG))
        else:
            sizeless.append(feature)
    return usable, sizeless

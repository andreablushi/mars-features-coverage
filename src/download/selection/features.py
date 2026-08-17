"""Feature selection: filter the catalog and give a point feature a size."""

from __future__ import annotations

from collections.abc import Sequence

from download import configs
from models.feature import Feature


def select_features(
    features: Sequence[Feature], *, names: Sequence[str] | None = None
) -> tuple[list[Feature], list[Feature]]:
    """Filter the catalog to the requested features and size the point ones.

    Matching is case insensitive, and the catalog's own spelling is preserved
    for querying. When no names are given, every feature is selected.

    A feature the catalogue gives no extent at all is a named position, and ODE
    rejects a query for one outright. Where the position stands for something
    with a real edge, a crater or a landing site, a box of
    configs.POINT_RADIUS_DEG is put around it and recorded as the box coverage
    is measured against. Where it stands for a classical albedo name, Arabia or
    Amazonis, there is no edge to recover: those names cover thousands of
    kilometres of diffuse ground, and any radius would be invented rather than
    measured.

    Args:
        features: The full feature catalog.
        names: Optional feature names to keep.

    Returns:
        A pair (usable, sizeless) where sizeless features carry no extent that
        could be recovered and were left unqueried.
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

"""Feature selection: filter the catalog and split off unqueryable features."""

from __future__ import annotations

from collections.abc import Sequence

from models.feature import Feature


def select_features(
    features: Sequence[Feature], *, names: Sequence[str] | None = None
) -> tuple[list[Feature], list[Feature]]:
    """Filter the catalog to the requested features and split off degenerate ones.

    Matching is case insensitive, and the catalog's own spelling is preserved
    for querying. When no names are given, every feature is selected.

    Args:
        features: The full feature catalog.
        names: Optional feature names to keep.

    Returns:
        A pair (usable, degenerate) where degenerate features have a zero or
        negative latitude span and cannot be queried.
    """
    # Format the requested names into a set
    wanted = {name.strip().lower() for name in names} if names else None

    # Filter the catalog to the requested features, preserving its own spelling
    selected = [
        feature
        for feature in features
        if wanted is None or feature.name.lower() in wanted
    ]

    # Split the selected features into usable and degenerate lists
    usable = [feature for feature in selected if not feature.is_degenerate]
    degenerate = [feature for feature in selected if feature.is_degenerate]
    return usable, degenerate

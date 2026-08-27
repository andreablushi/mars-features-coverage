"""Feature selection: keep the catalogue features that carry an extent."""

from __future__ import annotations

from collections.abc import Sequence

from models.feature import Feature


def select_features(features: Sequence[Feature]) -> list[Feature]:
    """Drop the features the catalogue gives no extent at all.

    Args:
        features: The full feature catalog.

    Returns:
        The features carrying an extent, in the order they came in.
    """
    return [feature for feature in features if not feature.is_point]

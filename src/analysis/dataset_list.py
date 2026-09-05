"""Reading the written selection back, which is how the building half reads it."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pyarrow.parquet as pq

import utils.disk.paths as paths
from analysis.models.feature import Feature
from analysis.selector.artifacts.write import FEATURES, OBSERVATIONS
from analysis.selector.models.selection import (
    SelectedFeature,
    SelectedObservation,
    Selection,
)


def read_dataset_list(root: Path = paths.SELECTION_ROOT) -> list[Selection]:
    """Read back every feature the selection stage searched, and what each keeps.

    A feature the filter refused is read back too, holding no observation, so a
    caller sees what to leave alone as plainly as what to download.

    Args:
        root: The directory the selection was written in.

    Returns:
        One entry per feature searched, in the order they were written, each
        carrying the observations it keeps, oldest first.

    Raises:
        FileNotFoundError: When no selection has been written there.
    """
    features = root / paths.SELECTED_FEATURES_NAME
    observations = root / paths.SELECTED_OBSERVATIONS_NAME
    if not features.is_file() or not observations.is_file():
        raise FileNotFoundError(f"no selection was written in {root}")
    kept: dict[tuple[str, str], list[SelectedObservation]] = {}
    for row in pq.read_table(observations, schema=OBSERVATIONS).to_pylist():
        observation = SelectedObservation(**row)
        held = kept.setdefault(
            (observation.feature_class, observation.feature_name), []
        )
        held.append(observation)
    return [
        Selection(
            feature=feature,
            observations=kept.get((feature.feature_class, feature.feature_name), []),
        )
        for feature in (
            SelectedFeature(**row)
            for row in pq.read_table(features, schema=FEATURES).to_pylist()
        )
    ]


def kept_features(picked: Sequence[Selection]) -> list[Feature]:
    """Read the ground of every feature the filter kept, as the selection holds it.

    Args:
        picked: What the search left of each feature, as the selection was read.

    Returns:
        The ground of each kept feature, in the order they were written.
    """
    return [
        Feature(
            name=one.feature.feature_name,
            feature_class=one.feature.feature_class,
            min_lat=one.feature.min_lat,
            max_lat=one.feature.max_lat,
            west_lon=one.feature.west_lon,
            east_lon=one.feature.east_lon,
        )
        for one in picked
        if one.feature.kept
    ]

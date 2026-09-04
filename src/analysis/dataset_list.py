"""Reading the written selection back, which is how the building half reads it."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pyarrow.parquet as pq

import utils.disk.paths as paths
from analysis.metadata.loaders.features import load_features
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


def read_kept_features(
    picked: Sequence[Selection], cache_dir: Path = paths.CATALOG_ROOT
) -> list[Feature]:
    """Read the catalogued extent of every feature the filter kept.

    The selection names a feature but not the ground it covers, and an
    instrument the selection cannot name is asked for that ground by its box.

    Args:
        picked: What the search left of each feature, as the selection was read.
        cache_dir: Directory holding the cached feature catalogue.

    Returns:
        The catalogue entry of each kept feature, in the order they were written.

    Raises:
        FileNotFoundError: When no feature catalogue is cached.
        KeyError: When the catalogue holds no entry for a kept feature.
    """
    catalogued = {
        (feature.feature_class, feature.name): feature
        for feature in load_features(cache_dir=cache_dir)
    }
    return [
        catalogued[(one.feature.feature_class, one.feature.feature_name)]
        for one in picked
        if one.feature.kept
    ]

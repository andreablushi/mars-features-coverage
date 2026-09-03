"""What the filter makes of the dataset, worked out once and kept.

A sweep of the whole catalogue costs minutes, and every section of a notebook
reads the same one, so the stats it leaves are held here from the first section
that asks for them. A run of the prediction pipeline leaves its own sweep on
disk, which is read first, and only a catalogue with none is swept again.
"""

from __future__ import annotations

from collections.abc import Sequence

from analysis.coverage.artifacts import indexing
from analysis.sampling import measuring, predicting, storing
from analysis.sampling.models.dataset import DatasetStats, SearchedFeature
from analysis.selector import selecting
from analysis.selector.models.survey import Study

_predicted: DatasetStats | None = None


def read_prediction(
    workers: int, progress: selecting.Progress | None = None
) -> DatasetStats:
    """Return what the filter written now would make of the dataset.

    Args:
        workers: How many processes to search on at once, as the run is configured.
        progress: Called with how many features are swept and how many there are.

    Returns:
        The stats the filter leaves over every measured feature.
    """
    global _predicted
    if _predicted is None:
        _predicted = storing.read_prediction()
    if _predicted is None:
        swept = sweep(indexing.catalogued_features(), workers, progress)
        _predicted = predicting.prediction(swept)
    return _predicted


def sweep(
    features: Sequence[selecting.FeatureName],
    workers: int,
    progress: selecting.Progress | None = None,
) -> list[SearchedFeature]:
    """Read every named feature's search as the stats it leaves.

    Args:
        features: The features to search, as class and name.
        workers: How many processes to search on at once, as the run is configured.
        progress: Called with how many features are done and how many there are.

    Returns:
        One entry per feature, in the order the features came in.
    """
    return selecting.search_features(features, measured, workers, progress)


def measured(feature: selecting.FeatureName, study: Study) -> SearchedFeature:
    """Read one feature's search as what it holds.

    Args:
        feature: The feature's class and name, as the catalogue spells them.
        study: What the search found over it.

    Returns:
        What the search left on it.
    """
    feature_class, _ = feature
    return SearchedFeature(
        feature_class=feature_class,
        iids=measuring.instruments_searched(study),
        stats=measuring.measured_feature(study),
    )

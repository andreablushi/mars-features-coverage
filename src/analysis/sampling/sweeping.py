"""What the filter makes of the dataset, worked out once and kept.

A sweep of the whole catalogue costs minutes, and every section of a notebook
reads the same one, so the stats it leaves are held here from the first section
that asks for them. A run of the prediction pipeline leaves its own sweep on
disk, which is read first, and only a catalogue with none is swept again.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor

from analysis.coverage.artifacts import indexing
from analysis.sampling import configs, measuring, predicting, searching, storing
from analysis.sampling.models.dataset import DatasetStats, SearchedFeature
from analysis.selector.artifacts import filter_config as filtering

FeatureName = tuple[str, str]
Progress = Callable[[int, int], None]

_predicted: DatasetStats | None = None


def read_prediction(
    workers: int = configs.DEFAULT_WORKERS, progress: Progress | None = None
) -> DatasetStats:
    """Return what the filter written now would make of the dataset.

    Args:
        workers: How many processes to search on at once.
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
    features: Sequence[FeatureName],
    workers: int = configs.DEFAULT_WORKERS,
    progress: Progress | None = None,
) -> list[SearchedFeature]:
    """Search every named feature under the filter.

    A search costs far more than the observations a feature holds, and the busiest
    features are a handful, so they are searched first. One of them starting last
    would run on alone for hours after the rest of the pool had drained.

    Args:
        features: The features to search, as class and name.
        workers: How many processes to search on at once.
        progress: Called with how many features are done and how many there are.

    Returns:
        One entry per feature, in the order the features came in.
    """
    searched: list[SearchedFeature | None] = [None for _ in features]
    observations = indexing.catalogued_observations()
    busiest_first = sorted(
        range(len(features)), key=lambda at: -observations.get(features[at], 0)
    )
    with ProcessPoolExecutor(max_workers=workers) as pool:
        found = pool.map(
            _search_feature, [features[at] for at in busiest_first], chunksize=1
        )
        for done, (at, entry) in enumerate(zip(busiest_first, found, strict=True), 1):
            searched[at] = entry
            if progress is not None:
                progress(done, len(features))
    return [entry for entry in searched if entry is not None]


def _search_feature(feature: FeatureName) -> SearchedFeature | None:
    """Search one feature under the filter.

    Args:
        feature: The feature's class and name.

    Returns:
        What the search left on it, and None where it has no set on disk.
    """
    feature_class, name = feature
    coverage = indexing.load_feature(feature_class, name)
    if not coverage:
        return None
    study = searching.study_feature(coverage, filtering.FILTER)
    return SearchedFeature(
        feature_class=feature_class,
        iids=measuring.instruments_searched(study),
        stats=measuring.measured_feature(study),
    )

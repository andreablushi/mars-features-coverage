"""What every strategy makes of the dataset, worked out once and kept.

A sweep of the whole catalogue costs minutes, and every section of a notebook
reads the same one, so the stats a strategy leaves are held here from the first
section that asks for them. A run of the prediction pipeline leaves its own
sweep on disk, which is read first, and only a strategy neither of them holds
is searched again.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from analysis.coverage import summary
from analysis.sampling import configs, measuring, predicting, searching, storing
from analysis.sampling.models.dataset import DatasetStats, SearchedFeature
from analysis.selector import strategies

FeatureName = tuple[str, str]
Progress = Callable[[int, int], None]

_predicted: dict[str, DatasetStats] = {}


def read_predictions(
    workers: int = configs.DEFAULT_WORKERS, progress: Progress | None = None
) -> dict[str, DatasetStats]:
    """Return what every strategy written would make of the dataset.

    Args:
        workers: How many processes to search on at once.
        progress: Called with how many features are swept and how many there are.

    Returns:
        The stats each strategy leaves, by name, in the order they are written.
    """
    missing = [name for name in strategies.STRATEGIES if name not in _predicted]
    if missing:
        _predicted.update(still_current(storing.read_predictions()))
        missing = [name for name in missing if name not in _predicted]
    if missing:
        swept = sweep(missing, summary.catalogued_features(), workers, progress)
        _predicted.update(predicting.predictions(swept))
    return {name: _predicted[name] for name in strategies.STRATEGIES}


def still_current(
    published: Mapping[str, tuple[str, DatasetStats]],
) -> dict[str, DatasetStats]:
    """Keep the strategies still written as they were when they were published.

    Args:
        published: The digest each strategy was filed under and its stats, by name.

    Returns:
        The stats of every strategy a run need not search again, by name.
    """
    # A strategy rewritten since it was published has to be searched again
    return {
        name: stats
        for name, (digest, stats) in published.items()
        if name in strategies.STRATEGIES and digest == strategies.digest(name)
    }


def sweep(
    strategy_names: Sequence[str],
    features: Sequence[FeatureName],
    workers: int = configs.DEFAULT_WORKERS,
    progress: Progress | None = None,
) -> list[SearchedFeature]:
    """Search every tile of every named feature under every strategy named.

    A search costs far more than the observations a feature holds, and the busiest
    features are a handful, so they are searched first. One of them starting last
    would run on alone for hours after the rest of the pool had drained.

    Args:
        strategy_names: The strategies to search under, by name.
        features: The features to search, as class and name.
        workers: How many processes to search on at once.
        progress: Called with how many features are done and how many there are.

    Returns:
        One entry per feature and strategy, in the order the features came in.
    """
    searched: list[list[SearchedFeature]] = [[] for _ in features]
    observations = summary.catalogued_observations()
    busiest_first = sorted(
        range(len(features)), key=lambda at: -observations.get(features[at], 0)
    )
    with ProcessPoolExecutor(max_workers=workers) as pool:
        found = pool.map(
            partial(_search_feature, strategy_names=tuple(strategy_names)),
            [features[at] for at in busiest_first],
            chunksize=1,
        )
        for done, (at, entry) in enumerate(zip(busiest_first, found, strict=True), 1):
            searched[at] = entry
            if progress is not None:
                progress(done, len(features))
    return [entry for feature in searched for entry in feature]


def _search_feature(
    feature: FeatureName, strategy_names: Sequence[str]
) -> list[SearchedFeature]:
    """Search every tile of one feature under every strategy named.

    Args:
        feature: The feature's class and name.
        strategy_names: The strategies to search under, by name.

    Returns:
        One entry per strategy, and nothing where the feature has no set on disk.
    """
    feature_class, name = feature
    coverage = summary.load_feature(feature_class, name)
    if not coverage:
        return []
    searched: list[SearchedFeature] = []
    for strategy_name in strategy_names:
        study = searching.study_feature(coverage, strategies.named(strategy_name))
        searched.append(
            SearchedFeature(
                strategy=strategy_name,
                feature_class=feature_class,
                iids=measuring.instruments_searched(study),
                tiles=measuring.measured_tiles(study),
            )
        )
    return searched

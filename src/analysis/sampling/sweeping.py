"""What the filter makes of the dataset, worked out once and kept.

Nothing is searched here. The selection stage wrote which features earned a
window and which observations they keep, and the sweep reads that back and
measures what those looks left on each feature. Every section of a notebook
reads the same stats, so they are held here from the first section that asks for
them. A run of the prediction pipeline leaves its own sweep on disk, which is
read first, and only a dataset with none is measured again.
"""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor

from analysis import dataset_list
from analysis.coverage.artifacts import indexing
from analysis.sampling import measuring, predicting, storing
from analysis.sampling.models.dataset import DatasetStats, SearchedFeature
from analysis.selector import selecting
from analysis.selector.artifacts import filter_config as filtering
from analysis.selector.models import track as timeline
from analysis.selector.models.selection import Selection

_predicted: DatasetStats | None = None


def read_prediction(
    workers: int, progress: selecting.Progress | None = None
) -> DatasetStats:
    """Return what the filter written now would make of the dataset.

    Args:
        workers: How many processes to measure on at once, as the run is configured.
        progress: Called with how many features are read and how many there are.

    Returns:
        The stats the filter leaves over every measured feature.

    Raises:
        FileNotFoundError: When neither a sweep nor a selection has been written.
    """
    global _predicted
    if _predicted is None:
        _predicted = storing.read_prediction()
    if _predicted is None:
        swept = sweep(dataset_list.read_dataset_list(), workers, progress)
        _predicted = predicting.prediction(swept)
    return _predicted


def sweep(
    picked: Sequence[Selection],
    workers: int,
    progress: selecting.Progress | None = None,
) -> list[SearchedFeature]:
    """Read what the selection kept of every feature as the stats it leaves.

    Args:
        picked: What the search left of each feature, as the selection wrote it.
        workers: How many processes to measure on at once, as the run is configured.
        progress: Called with how many features are done and how many there are.

    Returns:
        One entry per feature, in the order they came in, leaving out a feature
        holding no measured set on disk.
    """
    found: list[SearchedFeature] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for done, one in enumerate(pool.map(_measured, picked, chunksize=1), 1):
            if one is not None:
                found.append(one)
            if progress is not None:
                progress(done, len(picked))
    return found


def _measured(picked: Selection) -> SearchedFeature | None:
    """Measure one feature the selection kept, without searching it again.

    Args:
        picked: What the search left of it, and the observations it keeps.

    Returns:
        What those looks leave on it, and None where it has no measured set on disk.
    """
    feature = picked.feature
    coverage = indexing.load_feature(feature.feature_class, feature.feature_name)
    if not coverage:
        return None
    _, track = timeline.over(coverage, filtering.FILTER)
    if track is None:
        return SearchedFeature(feature_class=feature.feature_class, iids=[], stats=None)
    # The selection names the looks it keeps, which the timeline places in time
    at = {one.pdsid: index for index, one in enumerate(track.observations)}
    taken = sorted(at[one.pdsid] for one in picked.observations if one.pdsid in at)
    return SearchedFeature(
        feature_class=feature.feature_class,
        iids=measuring.instruments_searched(track),
        stats=measuring.measured_looks(track, feature, taken),
    )

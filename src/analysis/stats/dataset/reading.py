"""What the filter left of the whole dataset, read off the selection it wrote."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor

from analysis.coverage.artifacts import indexing
from analysis.selector.models.selection import Selection
from analysis.stats.artifacts import selection, storing
from analysis.stats.dataset import aggregating
from analysis.stats.feature import measuring
from analysis.stats.feature import reading as feature
from analysis.stats.models.dataset import DatasetStats
from analysis.stats.models.feature import FeatureStats

# Called with how many features are read and how many there are
Progress = Callable[[int, int], None]

_held: DatasetStats | None = None


def read_dataset_stats(workers: int, progress: Progress | None = None) -> DatasetStats:
    """Return what the filter left of the dataset, published or measured again.

    Args:
        workers: How many processes to measure on at once, as the run is configured.
        progress: Called with how many features are read and how many there are.

    Returns:
        The stats over every feature the selection searched.

    Raises:
        FileNotFoundError: When neither the stats nor a selection has been written.
    """
    global _held
    if _held is None:
        _held = storing.read_stats_file()
    if _held is None:
        picked = selection.read_selection()
        _held = aggregating.dataset_stats(
            measure_every_feature(picked, workers, progress), len(picked)
        )
    return _held


def measure_every_feature(
    picked: Sequence[Selection], workers: int, progress: Progress | None = None
) -> list[FeatureStats]:
    """Measure what the selection kept of every feature it searched.

    Args:
        picked: What the search left of each feature, as the selection wrote it.
        workers: How many processes to measure on at once, as the run is configured.
        progress: Called with how many features are done and how many there are.

    Returns:
        One entry per feature holding something to measure, in the order they
        came in, leaving out a feature with no measured set on disk.
    """
    found: list[FeatureStats] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for done, one in enumerate(
            pool.map(_measure_one_feature, picked, chunksize=1), 1
        ):
            if one is not None:
                found.append(one)
            if progress is not None:
                progress(done, len(picked))
    return found


def _measure_one_feature(picked: Selection) -> FeatureStats | None:
    """Measure one feature the selection searched.

    Args:
        picked: What the search left of it, and the observations it keeps.

    Returns:
        What those looks leave on it, and None where it has no measured set on
        disk or holds nothing measurable.
    """
    coverage = indexing.load_feature(
        picked.feature.feature_class, picked.feature.feature_name
    )
    if not coverage:
        return None
    looks = feature.place_kept_looks(coverage, picked)
    return None if looks is None else measuring.measured_feature(looks)

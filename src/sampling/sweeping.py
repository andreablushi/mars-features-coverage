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

from coverage import summary
from sampling import searching, storing
from sampling.models.dataset import DatasetStats
from sampling.models.searched import Searched
from sampling.stats import dataset, tiles
from selector import strategies

Named = tuple[str, str]
Progress = Callable[[int, int], None]

_held: dict[str, DatasetStats] = {}


def read(workers: int = 8, progress: Progress | None = None) -> dict[str, DatasetStats]:
    """Return what every strategy written would make of the dataset.

    Args:
        workers: How many processes to search on at once.
        progress: Called with how many features are swept and how many there are.

    Returns:
        The stats each strategy leaves, by name, in the order they are written.
    """
    missing = [name for name in strategies.STRATEGIES if name not in _held]
    if missing:
        _held.update(unchanged(storing.loaded()))
        missing = [name for name in missing if name not in _held]
    if missing:
        found = sweep(missing, summary.catalogued_features(), workers, progress)
        _held.update(dataset.read(found))
    return {name: _held[name] for name in strategies.STRATEGIES}


def unchanged(
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
    under: Sequence[str],
    wanted: Sequence[Named],
    workers: int = 8,
    progress: Progress | None = None,
) -> list[Searched]:
    """Search every tile of every named feature under every strategy named.

    A search costs far more than the observations a feature holds, and the busiest
    features are a handful, so they are searched first. One of them starting last
    would run on alone for hours after the rest of the pool had drained.

    Args:
        under: The strategies to search under, by name.
        wanted: The features to search, as class and name.
        workers: How many processes to search on at once.
        progress: Called with how many features are done and how many there are.

    Returns:
        One entry per feature and strategy, in the order the features came in.
    """
    found: list[list[Searched]] = [[] for _ in wanted]
    search = partial(_searched, under=tuple(under))
    counted = summary.catalogued_observations()
    order = sorted(range(len(wanted)), key=lambda place: -counted.get(wanted[place], 0))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        searched = pool.map(search, [wanted[place] for place in order], chunksize=1)
        for done, (place, entry) in enumerate(zip(order, searched, strict=True), 1):
            found[place] = entry
            if progress is not None:
                progress(done, len(wanted))
    return [entry for held in found for entry in held]


def _searched(named: Named, under: Sequence[str]) -> list[Searched]:
    """Search every tile of one feature under every strategy named.

    Args:
        named: The feature's class and name.
        under: The strategies to search under, by name.

    Returns:
        One entry per strategy, and nothing where the feature has no set on disk.
    """
    feature_class, name = named
    coverage = summary.load_feature(feature_class, name)
    if not coverage:
        return []
    found: list[Searched] = []
    for chosen in under:
        study = searching.study(coverage, strategies.named(chosen))
        found.append(
            Searched(
                strategy=chosen,
                iids=tiles.instruments(study),
                measured=tiles.measured(study),
            )
        )
    return found

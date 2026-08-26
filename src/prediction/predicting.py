"""What every strategy makes of the dataset, worked out once and kept.

A sweep of the whole catalogue costs minutes, and every section of a notebook
reads the same one, so the stats a strategy leaves are held here from the first
section that asks for them. A run of the prediction pipeline leaves its own
sweep on disk, which is read first, and only a strategy neither of them holds
is searched again.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from prediction import storing
from prediction.models.dataset import DatasetStats
from prediction.models.searched import Searched
from prediction.stats import dataset, tiles
from storage import summary
from survey import strategies, studying

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
        _held.update(storing.loaded())
        missing = [name for name in missing if name not in _held]
    if missing:
        found = sweep(missing, summary.catalogued_features(), workers, progress)
        _held.update(dataset.read(found))
    return {name: _held[name] for name in strategies.STRATEGIES}


def sweep(
    under: Sequence[str],
    wanted: Sequence[Named],
    workers: int = 8,
    progress: Progress | None = None,
) -> list[Searched]:
    """Search every tile of every named feature under every strategy named.

    Args:
        under: The strategies to search under, by name.
        wanted: The features to search, as class and name.
        workers: How many processes to search on at once.
        progress: Called with how many features are done and how many there are.

    Returns:
        One entry per feature and strategy, in the order the features came in.
    """
    found: list[Searched] = []
    searching = partial(_searched, under=tuple(under))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for done, searched in enumerate(pool.map(searching, wanted, chunksize=1), 1):
            found.extend(searched)
            if progress is not None:
                progress(done, len(wanted))
    return found


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
        study = studying.study(coverage, strategies.named(chosen))
        found.append(
            Searched(
                strategy=chosen,
                iids=tiles.instruments(study),
                measured=tiles.measured(study),
            )
        )
    return found

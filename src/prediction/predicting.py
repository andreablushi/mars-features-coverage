"""What every strategy makes of the dataset, worked out once and kept.

A sweep of the whole catalogue costs minutes, and every section of a notebook
reads the same one, so the stats a strategy leaves are held here from the first
section that asks for them. A run of the prediction pipeline leaves its own
sweep on disk, which is read first, and only a strategy neither of them holds
is searched again.
"""

from __future__ import annotations

from prediction import storing, sweeping
from prediction.stats import dataset
from prediction.stats.dataset import DatasetStats
from prediction.sweeping import Progress
from storage import summary
from survey import strategies

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
        found = sweeping.sweep(
            missing, summary.catalogued_features(), workers, progress
        )
        _held.update(dataset.read(found))
    return {name: _held[name] for name in strategies.STRATEGIES}

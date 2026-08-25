"""What every strategy makes of the dataset, worked out once and kept."""

from __future__ import annotations

from survey import strategies
from visualization.dataset import progress, saving
from visualization.dataset.stats import dataset
from visualization.dataset.stats.dataset import DatasetStats

_held: dict[str, DatasetStats] = {}


def read(workers: int = 8) -> dict[str, DatasetStats]:
    """Return what every strategy written would make of the dataset.

    Args:
        workers: How many processes to search on at once.

    Returns:
        The stats each strategy leaves, by name, in the order they are written.
    """
    missing = [name for name in strategies.STRATEGIES if name not in _held]
    if missing:
        _held.update(saving.loaded())
        missing = [name for name in missing if name not in _held]
    if missing:
        _held.update(dataset.read(progress.swept(missing, workers=workers)))
    return {name: _held[name] for name in strategies.STRATEGIES}

"""What every strategy makes of the dataset, worked out once and kept.

A sweep of the whole catalogue costs minutes, and every section of the
notebook reads the same one, so the stats a strategy leaves are held here from
the first section that asks for them. Only a strategy nothing is held for is
searched again.
"""

from __future__ import annotations

from survey import strategies
from visualization.dataset import progress
from visualization.dataset.stats import dataset
from visualization.dataset.stats.dataset import DatasetStats

_held: dict[str, DatasetStats] = {}


def read(workers: int = 8) -> dict[str, DatasetStats]:
    """Return what every strategy written would make of the dataset.

    Every tile of every feature computed locally is searched, so what comes
    back is the whole catalogue and not a sample of it.

    Args:
        workers: How many processes to search on at once.

    Returns:
        The stats each strategy leaves, by strategy name, in the order the
        strategies are written.
    """
    missing = [name for name in strategies.STRATEGIES if name not in _held]
    if missing:
        _held.update(dataset.read(progress.swept(missing, workers=workers)))
    return {name: _held[name] for name in strategies.STRATEGIES}

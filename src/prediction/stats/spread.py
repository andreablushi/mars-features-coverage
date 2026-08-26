"""Reading one measurement off every tile that took it."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from prediction.models.spread import Spread


def over(values: Sequence[float]) -> Spread:
    """Read one measurement off every tile that took it.

    Args:
        values: The measurement, one per tile, in any order.

    Returns:
        The spread, empty at nought where no tile took it.
    """
    if not values:
        return Spread(0.0, 0.0, 0.0, 0.0, 0.0, 0)
    return Spread(
        mean=statistics.fmean(values),
        middle=statistics.median(values),
        deviation=statistics.pstdev(values) if len(values) > 1 else 0.0,
        low=min(values),
        high=max(values),
        counted=len(values),
    )

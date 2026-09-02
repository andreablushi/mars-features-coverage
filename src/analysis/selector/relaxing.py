"""Reading the filter as asking for a look and no ground in particular."""

from __future__ import annotations

import dataclasses

from analysis.selector.models.filter import Filter


def unfloored(criteria: Filter) -> Filter:
    """Read the filter as asking each instrument for a single cell of a feature.

    Everything else it asks is left alone: the instruments each constraint names,
    the pixels a look has to land before it counts, and how long a window may run.
    Only the ground each instrument is asked for is dropped, so a feature the
    search refused still earns the window it came closest with.

    Args:
        criteria: What the instruments are really asked for.

    Returns:
        The same filter marked as unfloored, asking for no ground.
    """
    return dataclasses.replace(
        criteria,
        unfloored=True,
        constraints=tuple(
            dict.fromkeys(constraint, 0.0) for constraint in criteria.constraints
        ),
    )

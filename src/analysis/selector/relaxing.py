"""Reading a strategy as asking for a look and no ground in particular."""

from __future__ import annotations

import dataclasses

from analysis.selector.models.strategy import Strategy

# What the relaxed reading is called, so a cache never mistakes it for the real one.
UNFLOORED = " (unfloored)"


def unfloored(strategy: Strategy) -> Strategy:
    """Read a strategy as asking each instrument for a single cell of a feature.

    Everything else it asks is left alone: the instruments each constraint names,
    the pixels a look has to land before it counts, and how long a window may run.
    Only the ground each instrument is asked for is dropped, so a feature the
    search refused still earns the window it came closest with.

    Args:
        strategy: What the instruments are really asked for.

    Returns:
        The same strategy under a name of its own, asking for no ground.
    """
    return dataclasses.replace(
        strategy,
        name=f"{strategy.name}{UNFLOORED}",
        constraints=tuple(
            dict.fromkeys(constraint, 0.0) for constraint in strategy.constraints
        ),
    )

"""The weightings of the instruments a search can be run under, side by side.

Each strategy is one file, named in the registry below and nowhere else, so a
strategy that loses the comparison is removed by deleting its file and the two
lines that mention it.
"""

from __future__ import annotations

from survey.models.strategy import Strategy
from survey.strategies.imaged import IMAGED
from survey.strategies.presence import PRESENCE
from survey.strategies.spectral import SPECTRAL

STRATEGIES: dict[str, Strategy] = {
    strategy.name: strategy for strategy in (PRESENCE, IMAGED, SPECTRAL)
}


def named(name: str) -> Strategy:
    """Return the strategy one name stands for.

    Args:
        name: The strategy's name, as its own file spells it.

    Returns:
        The strategy.

    Raises:
        KeyError: When no strategy goes by that name.
    """
    return STRATEGIES[name]

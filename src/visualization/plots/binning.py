"""The time bins the figures drawn over a range of months share."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from models.results import SetCoverage
from visualization import configs
from visualization.selectors.window import Window, month_edges


def edges(coverage: Sequence[SetCoverage], window: Window) -> list[datetime]:
    """Return the bin edges a panel covers, at the configured width.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range to bin over, open at either end to take the
            record's own extent there.

    Returns:
        The edges in order, one more than there are bins.
    """
    first = window.start or min(entry.summary.t_first for entry in coverage)
    last = window.end or max(entry.summary.t_last for entry in coverage)
    return month_edges(first, last, configs.DENSITY_BIN_MONTHS)


def name() -> str:
    """Name the configured bin width, for a title or an axis label.

    Returns:
        The bin width as it reads in a sentence, such as "month" or
        "3 months".
    """
    months = configs.DENSITY_BIN_MONTHS
    return "month" if months == 1 else f"{months} months"

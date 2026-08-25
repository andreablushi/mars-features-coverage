"""Which of the downloaded instrument sets the figures are drawn for."""

from __future__ import annotations

from collections.abc import Sequence

import utils.disk.settings as settings
from models.results import SetCoverage


def plotted(coverage: Sequence[SetCoverage]) -> list[SetCoverage]:
    """Keep the instrument sets the config draws, in the order it names them.

    Args:
        coverage: Every instrument set loaded for one feature.

    Returns:
        The sets the config names, in the order it names them.
    """
    config = settings.load()
    wanted = config.plot_instrument_sets
    # A config naming no set draws every one, in the order the config ranks them
    keys = {chosen.key for chosen in wanted or ()}
    drawn = (
        list(coverage)
        if wanted is None
        else [one for one in coverage if one.summary.set_key in keys]
    )
    ranks = {
        chosen.key: rank for rank, chosen in enumerate(wanted or config.instrument_sets)
    }
    return sorted(
        drawn, key=lambda instrument: ranks.get(instrument.summary.set_key, len(ranks))
    )

"""Which of the downloaded instrument sets the figures are drawn for."""

from __future__ import annotations

from collections.abc import Sequence

import utils.settings as settings
from models.instrument import InstrumentSet
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
    drawn = _named(coverage, wanted) if wanted is not None else list(coverage)
    ranks = {
        chosen.key: rank for rank, chosen in enumerate(wanted or config.instrument_sets)
    }
    return sorted(drawn, key=lambda entry: ranks.get(entry.summary.set_key, len(ranks)))


def _named(
    coverage: Sequence[SetCoverage], wanted: Sequence[InstrumentSet]
) -> list[SetCoverage]:
    """Keep only the sets the config asks the figures to draw.

    Args:
        coverage: Every instrument set loaded for one feature.
        wanted: The instrument sets the config names.

    Returns:
        Those of them the feature holds, in the order they came in.
    """
    keys = {chosen.key for chosen in wanted}
    return [entry for entry in coverage if entry.summary.set_key in keys]

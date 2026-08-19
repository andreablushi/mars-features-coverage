"""Which of the downloaded instrument sets the figures are drawn for."""

from __future__ import annotations

from collections.abc import Sequence

import utils.settings as settings
from models.results import SetCoverage


def plotted(coverage: Sequence[SetCoverage]) -> list[SetCoverage]:
    """Keep only the instrument sets the config asks the figures to draw.

    The config is read on every call, so narrowing the list and confirming a
    feature again redraws without restarting the kernel.

    Args:
        coverage: Every instrument set loaded for one feature.

    Returns:
        The sets the config names, in the order they came in, or all of them
        when it names none.
    """
    wanted = settings.load().plot_instrument_sets
    if wanted is None:
        return list(coverage)
    keys = {chosen.key for chosen in wanted}
    return [entry for entry in coverage if entry.summary.set_key in keys]

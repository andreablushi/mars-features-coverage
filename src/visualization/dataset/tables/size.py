"""How big a dataset each strategy would leave, and how good its tiles are."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from sampling.models.dataset import DatasetStats
from visualization.common import tables, wording
from visualization.common.tables import Row

_HEADINGS = ("Strategy", "Tiles searched", "Tiles kept", "Share kept")


def final(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate the dataset each strategy would leave behind.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    rows: list[Row] = []
    for stats in read.values():
        held = stats.held
        rows.append(
            (
                stats.strategy,
                f"{held.searched:,}",
                f"{held.kept:,}",
                f"{held.kept / held.searched:.1%}"
                if held.searched
                else wording.NOTHING,
            )
        )
    return tables.written("The dataset each strategy would leave", _HEADINGS, rows)

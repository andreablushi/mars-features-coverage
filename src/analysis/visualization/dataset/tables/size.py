"""How big a dataset each strategy would leave, and how good its features are."""

from __future__ import annotations

from collections.abc import Mapping

import ipywidgets as widgets

from analysis.sampling.models.dataset import DatasetStats
from analysis.utils import settings
from analysis.visualization.common import tables, wording
from analysis.visualization.common.tables import Row


def final(read: Mapping[str, DatasetStats]) -> widgets.Widget:
    """Tabulate the dataset each strategy would leave behind.

    Args:
        read: What each strategy made of the features swept, by strategy name.

    Returns:
        The table as a widget.
    """
    iids = list(dict.fromkeys(one.iid for one in settings.load().instrument_sets))
    headings = (
        "Strategy",
        "Features searched",
        "Features kept",
        "Share kept",
        *(f"{iid} observations offered" for iid in iids),
    )
    rows: list[Row] = []
    for stats in read.values():
        held = stats.held
        observations: list[str] = []
        for iid in iids:
            measured = stats.offered.get(iid)
            observations.append(
                f"{measured.mean * measured.counted:,.0f}"
                if measured and measured.counted
                else wording.NOTHING
            )
        rows.append(
            (
                stats.strategy,
                f"{held.searched:,}",
                f"{held.kept:,}",
                f"{held.kept / held.searched:.1%}"
                if held.searched
                else wording.NOTHING,
                *observations,
            )
        )
    return tables.written("The dataset each strategy would leave", headings, rows)

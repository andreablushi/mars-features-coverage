"""How big a dataset the filter would leave, and how good its features are."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.stats.models.dataset import DatasetStats
from analysis.visualization.common import tables, wording
from analysis.visualization.common.tables import Row

_HEADINGS = ("Statistic", "Value")


def final(read: DatasetStats) -> widgets.Widget:
    """Tabulate the dataset the filter would leave behind.

    Args:
        read: What the filter made of the features swept.

    Returns:
        The table as a widget, read down rather than across since one filter
        leaves one dataset to report.
    """
    held = read.held
    rows: list[Row] = [
        ("Features searched", f"{held.searched:,}"),
        ("Features kept", f"{held.kept:,}"),
        (
            "Share kept",
            f"{held.kept / held.searched:.1%}" if held.searched else wording.NOTHING,
        ),
    ]
    for iid in read.iids:
        measured = read.offered.get(iid)
        rows.append(
            (
                f"{iid} observations offered",
                f"{measured.mean * measured.counted:,.0f}"
                if measured and measured.counted
                else wording.NOTHING,
            )
        )
    return tables.written("The dataset the filter would leave", _HEADINGS, rows)

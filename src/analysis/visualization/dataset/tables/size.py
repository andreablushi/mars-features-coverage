"""How big a dataset the filter leaves, and how good its features are."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.stats.models.dataset import DatasetStats
from analysis.visualization.common import tables
from analysis.visualization.common.models.tables import Row

_HEADINGS = ("Statistic", "Value")


def final(read: DatasetStats) -> widgets.Widget:
    """Tabulate the dataset the filter leaves behind."""
    held = read.held
    rows: list[Row] = [
        ("Features searched", f"{held.searched:,}"),
        ("Features kept", f"{held.kept:,}"),
        ("Share kept", f"{held.kept / held.searched:.1%}"),
    ]
    for iid in read.iids:
        measured = read.offered[iid]
        rows.append(
            (
                f"{iid} observations offered",
                f"{measured.mean * measured.counted:,.0f}",
            )
        )
    return tables.written("The dataset the filter leaves", _HEADINGS, rows)

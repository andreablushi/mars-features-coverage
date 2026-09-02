"""How big a dataset the filter would leave, and how good its features are."""

from __future__ import annotations

import ipywidgets as widgets

from analysis.sampling.models.dataset import DatasetStats
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
    rows.extend(
        (f"{iid} observations offered", _offered(read, iid)) for iid in read.iids
    )
    return tables.written("The dataset the filter would leave", _HEADINGS, rows)


def _offered(read: DatasetStats, iid: str) -> str:
    """Write how many observations one instrument landed on the features searched.

    Args:
        read: What the filter made of the features swept.
        iid: The instrument to write.

    Returns:
        The count over every feature searched, or that it landed none.
    """
    measured = read.offered.get(iid)
    if measured is None or not measured.counted:
        return wording.NOTHING
    return f"{measured.mean * measured.counted:,.0f}"

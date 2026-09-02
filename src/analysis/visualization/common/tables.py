"""The one table every panel writes its rows into."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import ipywidgets as widgets
import pandas as pd

Row = Sequence[str]


def written(title: str, headings: Sequence[str], rows: Sequence[Row]) -> widgets.HTML:
    """Write a table out as a panel.

    Args:
        title: The bold line above it.
        headings: What each column holds.
        rows: The rows, each holding one cell per heading.

    Returns:
        The panel.
    """
    frame = pd.DataFrame(rows, columns=list(headings))
    return widgets.HTML(f"<b>{escape(title)}</b>{frame.to_html(index=False, border=0)}")

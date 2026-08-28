"""The one table every panel writes its rows into."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape

import ipywidgets as widgets

from visualization.common import panels


@dataclass(frozen=True, slots=True)
class Mark:
    """One cell written in a colour of its own.

    Attributes:
        text: What the cell reads.
        colour: The colour to write it in.
    """

    text: str
    colour: str


Cell = str | Mark
Row = Sequence[Cell]


def written(
    title: str,
    headings: Sequence[str],
    rows: Sequence[Row],
    groups: Sequence[int] = (),
) -> widgets.HTML:
    """Write a table out as a panel.

    Args:
        title: The bold line above it.
        headings: What each column holds, the first ranged left and the rest right.
        rows: The rows, each holding one cell per heading.
        groups: The rows that open a group, each ruled off from the one above it.

    Returns:
        The panel.
    """
    opening = set(groups)
    body = "".join(_row(cells, at in opening) for at, cells in enumerate(rows))
    return widgets.HTML(
        f"""<div style="font-family: sans-serif; font-size: 13px;">
          <div style="font-weight: 600; margin-bottom: 8px;">{escape(title)}</div>
          <table style="border-collapse: collapse;">
            <tr>{"".join(_heading(name, at) for at, name in enumerate(headings))}</tr>
            {body}
          </table>
        </div>"""
    )


def _heading(name: str, at: int) -> str:
    """Build one column heading.

    Args:
        name: What the column holds.
        at: Which column it is, since the first is ranged left.

    Returns:
        The heading cell.
    """
    align = "left" if at == 0 else "right"
    return (
        f'<th style="text-align: {align}; padding: 4px 14px 4px 0;'
        f' border-bottom: 1px solid #c4c4c4; font-weight: 600;">{escape(name)}</th>'
    )


def _row(cells: Row, opening: bool) -> str:
    """Build one row.

    Args:
        cells: One cell per column.
        opening: Whether it opens a group, so a rule is drawn above it.

    Returns:
        The row.
    """
    return (
        f"<tr>{''.join(_cell(cell, at, opening) for at, cell in enumerate(cells))}</tr>"
    )


def _cell(cell: Cell, at: int, opening: bool) -> str:
    """Build one cell.

    Args:
        cell: What it reads, and the colour to write it in when it carries one.
        at: Which column it is, since the first is ranged left.
        opening: Whether its row opens a group, so it is set off from the one above.

    Returns:
        The cell.
    """
    align = "left" if at == 0 else "right"
    marked = isinstance(cell, Mark)
    style = f" color: {cell.colour}; font-weight: 600;" if marked else ""
    text = cell.text if marked else cell
    # A group opens on a rule heavier than the hairline every row already carries
    above = f"border-top: 2px solid {panels.GREY};" if opening else ""
    return (
        f'<td style="text-align: {align};'
        f" padding: {'14px' if opening else '4px'} 14px 4px 0;"
        f' border-bottom: 1px solid #ebebeb;{above}{style}">{escape(text)}</td>'
    )

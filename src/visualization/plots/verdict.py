"""Whether the feature on show belongs in the dataset, and what decided it."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import ipywidgets as widgets

from campaign.verdict import Check, Verdict
from models.results import SetCoverage
from visualization import campaigns, panels
from visualization.selectors.window import Window

# How a feature that belongs in the dataset is marked, and one that does not.
VERDICT_PASS = "#2e7d32"
VERDICT_FAIL = "#c62828"
VERDICT_KEPT = "In the dataset"
VERDICT_LEFT = "Left out of the dataset"


_HEADINGS = ("Asked of the feature", "What it holds", "Least it can hold", "")
_MARKS = {True: "PASS", False: "FAIL"}
_NOTE = "read only"
_ADVISORY = "Rows with nothing in the third column are there to be read. They "
_ADVISORY += "have no say in the verdict."


def plot(coverage: Sequence[SetCoverage], window: Window) -> widgets.Widget:
    """Report whether the feature is worth putting in the dataset, and why.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range the panels are shown over.

    Returns:
        The scorecard as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    verdict = campaigns.assessed(coverage, window)
    rows = "".join(_row(check) for check in verdict.checks)
    return widgets.HTML(
        f"""<div style="font-family: sans-serif; font-size: 13px;">
          <div style="font-weight: 600; margin-bottom: 2px;">
            {escape(panels.title(coverage))}  -  in the dataset or not
          </div>
          {_headline(verdict)}
          <table style="border-collapse: collapse;">
            <tr>{"".join(_heading(name) for name in _HEADINGS)}</tr>
            {rows}
          </table>
          <div style="color: {panels.GREY}; font-size: 12px; margin-top: 8px;">
            {escape(_ADVISORY)}
          </div>
        </div>"""
    )


def _headline(verdict: Verdict) -> str:
    """Write the verdict itself, above everything that decided it.

    Args:
        verdict: What the feature was judged to be.

    Returns:
        The banner, coloured by which way it went.
    """
    colour = VERDICT_PASS if verdict.kept else VERDICT_FAIL
    said = VERDICT_KEPT if verdict.kept else VERDICT_LEFT
    return (
        f'<div style="color: {colour}; font-size: 15px; font-weight: 600;'
        f' margin: 6px 0 8px 0;">{escape(said)}</div>'
    )


def _heading(name: str) -> str:
    """Build one column heading of the scorecard.

    Args:
        name: What the column holds.

    Returns:
        The heading cell, the name ranged left and the numbers right.
    """
    align = "left" if name == _HEADINGS[0] else "right"
    return (
        f'<th style="text-align: {align}; padding: 4px 14px 4px 0;'
        f' border-bottom: 1px solid #c4c4c4; font-weight: 600;">{escape(name)}</th>'
    )


def _row(check: Check) -> str:
    """Build one requirement's row of the scorecard.

    Args:
        check: The requirement and what the feature answered.

    Returns:
        The row, its mark coloured only where the mark decides something.
    """
    if not check.required:
        colour, mark = panels.GREY, _NOTE
    else:
        colour = VERDICT_PASS if check.passed else VERDICT_FAIL
        mark = _MARKS[check.passed]
    return (
        f"<tr>{_cell(check.name, left=True)}{_cell(check.value)}"
        f"{_cell(check.wanted)}{_cell(mark, colour=colour)}</tr>"
    )


def _cell(value: str, left: bool = False, colour: str = "") -> str:
    """Build one cell of the scorecard.

    Args:
        value: What the cell reads.
        left: Whether it is the name column rather than a number.
        colour: The colour to write it in, or an empty string for the default.

    Returns:
        The cell.
    """
    align = "left" if left else "right"
    style = f" color: {colour}; font-weight: 600;" if colour else ""
    return (
        f'<td style="text-align: {align}; padding: 4px 14px 4px 0;'
        f' border-bottom: 1px solid #ebebeb;{style}">{escape(value)}</td>'
    )

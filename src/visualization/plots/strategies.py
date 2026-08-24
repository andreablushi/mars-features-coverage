"""What each way of weighting the instruments would keep of this feature."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from html import escape

import ipywidgets as widgets

from models.results import SetCoverage
from survey import strategies
from survey.models.verdict import Verdict
from utils.maths import quantities
from visualization import panels, surveys

_NOTHING = "nothing"
_RUNNING = " (running)"
_HEADINGS = (
    "Strategy",
    "Instruments insisted on",
    "Tiles kept",
    "Ground kept",
    "Middle window",
    "Ground two instruments reach",
    "Observations",
)


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Tabulate what every strategy would keep of the feature on show.

    The strategies differ only in which instruments they insist on and how
    much of a tile each of them has to reach, so reading them side by side is
    reading what those demands cost and what they buy.

    Args:
        coverage: The feature's instrument sets, in the order the config names
            them.

    Returns:
        The table as a widget, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    area_km2 = coverage[0].summary.feature_area_km2
    rows = "".join(
        _row(name, surveys.assessed(coverage, strategy), area_km2)
        for name, strategy in strategies.STRATEGIES.items()
    )
    return widgets.HTML(
        f"""<div style="font-family: sans-serif; font-size: 13px;">
          <div style="font-weight: 600; margin-bottom: 8px;">
            {escape(panels.title(coverage))}  -  strategies side by side
          </div>
          <table style="border-collapse: collapse;">
            <tr>{"".join(_heading(name) for name in _HEADINGS)}</tr>
            {rows}
          </table>
        </div>"""
    )


def _heading(name: str) -> str:
    """Build one column heading of the table.

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


def _row(name: str, verdict: Verdict, area_km2: float) -> str:
    """Build one strategy's row of the table.

    Args:
        name: The strategy's name.
        verdict: What the feature was judged to be under it.
        area_km2: How much ground the feature covers.

    Returns:
        The row, the strategy the run is configured with marked as such.
    """
    running = name == surveys.SHOWN.name
    ground = sum(survey.area_km2 for survey in verdict.surveys)
    shared = verdict.overlaps.get(2, 0.0)
    cells = [
        _asked(name),
        f"{len(verdict.surveys):,} of {verdict.tiles:,}",
        _ground(ground, area_km2),
        _middle(verdict),
        _ground(shared, area_km2),
        f"{verdict.taken:,}",
    ]
    written = name + (_RUNNING if running else "")
    return (
        f"<tr>{_cell(written, left=True, bold=running)}"
        f"{''.join(_cell(value, bold=running) for value in cells)}</tr>"
    )


def _asked(name: str) -> str:
    """Say what one strategy insists on, instrument by instrument.

    Args:
        name: The strategy's name.

    Returns:
        Each instrument and the share of a tile it has to reach.
    """
    return ", ".join(
        " or ".join(f"{iid} {share:.0%}" for iid, share in demand.items())
        for demand in strategies.named(name).demands
    )


def _middle(verdict: Verdict) -> str:
    """Write how long the middle tile's window lasts.

    Args:
        verdict: What the feature was judged to be.

    Returns:
        The length, or that there is nothing to measure.
    """
    if not verdict.surveys:
        return _NOTHING
    return quantities.duration(
        statistics.median(survey.days for survey in verdict.surveys)
    )


def _ground(ground_km2: float, area_km2: float) -> str:
    """Write an amount of ground and what share of the feature it is.

    Args:
        ground_km2: The ground in square kilometres.
        area_km2: How much ground the feature covers.

    Returns:
        The ground, or that there is none.
    """
    if not ground_km2:
        return _NOTHING
    return f"{quantities.area(ground_km2)}, {ground_km2 / area_km2:.0%}"


def _cell(value: str, left: bool = False, bold: bool = False) -> str:
    """Build one cell of the table.

    Args:
        value: What the cell reads.
        left: Whether it is the name column rather than a number.
        bold: Whether the row is the strategy the run is configured with.

    Returns:
        The cell.
    """
    align = "left" if left else "right"
    weight = " font-weight: 600;" if bold else ""
    return (
        f'<td style="text-align: {align}; padding: 4px 14px 4px 0;'
        f' border-bottom: 1px solid #ebebeb;{weight}">{escape(value)}</td>'
    )

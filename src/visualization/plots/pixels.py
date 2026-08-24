"""How much each instrument gathered inside the windows the tiles earned."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import ipywidgets as widgets

from models.results import Event, SetCoverage
from utils.maths import mask as packing
from utils.maths import quantities
from visualization import panels, surveys
from visualization.surveys import Stretch

_NO_WINDOW = "No tile of this feature holds a window worth keeping."
_UNMEASURED = "not measured"
_HEADINGS = (
    "Instrument",
    "Observations",
    "Pixels in the windows",
    "Pixels in the feature",
    "Ground reached in the windows",
)


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Tabulate what each instrument gathered inside the chosen windows.

    A feature is searched a tile at a time and every tile keeps its own
    window, so an observation counts here when it was taken while any of them
    was open, and counts once however many of them it was.

    Args:
        coverage: The feature's instrument sets, widest coverage first.

    Returns:
        The table as a widget, or the grey panel when there is none to draw.
    """
    if not coverage:
        return panels.unavailable()
    verdict = surveys.assessed(coverage)
    if not verdict.surveys:
        return panels.unavailable(_NO_WINDOW)
    summary = coverage[0].summary
    cell_km2 = summary.cell_km2
    open_for = surveys.stretches(verdict.surveys)
    rows = "".join(_row(instrument, open_for, cell_km2) for instrument in coverage)
    return widgets.HTML(
        f"""<div style="font-family: sans-serif; font-size: 13px;">
          <div style="font-weight: 600; margin-bottom: 2px;">
            {escape(panels.title(coverage))}  -  inside the windows the tiles earned
          </div>
          <div style="color: {panels.GREY}; font-size: 12px; font-weight: 600;
                      margin-bottom: 8px;">
            {len(verdict.surveys):,} tiles, {_when(open_for)}
          </div>
          <table style="border-collapse: collapse;">
            <tr>{"".join(_heading(name) for name in _HEADINGS)}</tr>
            {rows}
          </table>
        </div>"""
    )


def _when(open_for: Sequence[Stretch]) -> str:
    """Say when the windows were open and over how many stretches of time.

    Args:
        open_for: The stretches of time the windows are open over.

    Returns:
        The line under the title.
    """
    counted = (
        "one stretch of time"
        if len(open_for) == 1
        else f"{len(open_for):,} stretches of time"
    )
    return f"{counted}, {open_for[0][0]:%Y-%m-%d} to {open_for[-1][1]:%Y-%m-%d}"


def _inside(observations: Sequence[Event], open_for: Sequence[Stretch]) -> list[Event]:
    """Keep the observations taken while any window was open.

    Args:
        observations: One instrument set's observations, in chronological
            order.
        open_for: The stretches of time the windows are open over.

    Returns:
        Those of them falling inside one, each once.
    """
    return [
        observation
        for observation in observations
        if any(opened <= observation.t_start <= closed for opened, closed in open_for)
    ]


def _heading(name: str) -> str:
    """Build one column heading of the table.

    Args:
        name: What the column holds.

    Returns:
        The heading cell, numbers ranged right as their values are.
    """
    align = "left" if name == "Instrument" else "right"
    return (
        f'<th style="text-align: {align}; padding: 4px 14px 4px 0;'
        f' border-bottom: 1px solid #c4c4c4; font-weight: 600;">{escape(name)}</th>'
    )


def _row(instrument: SetCoverage, open_for: Sequence[Stretch], cell_km2: float) -> str:
    """Build one instrument set's row of the table.

    Args:
        instrument: The instrument set the row describes.
        open_for: The stretches of time its observations are counted inside.
        cell_km2: How much ground one cell of the feature's grid covers.

    Returns:
        The row, saying so where the artifacts carry no pixel count at all.
    """
    held = _inside(instrument.events, open_for)
    inside, total = _pixels(held), instrument.summary.pixels
    ground = _ground(held, cell_km2)
    if inside is None or total is None:
        cells = [f"{len(held):,}", _UNMEASURED, _UNMEASURED, ground]
    else:
        cells = [
            f"{len(held):,}",
            quantities.compact(inside),
            quantities.compact(total),
            ground,
        ]
    return (
        f"<tr>{_cell(instrument.label, left=True)}"
        f"{''.join(_cell(value) for value in cells)}</tr>"
    )


def _cell(value: str, left: bool = False) -> str:
    """Build one cell of the table.

    Args:
        value: What the cell reads.
        left: Whether it is the name column rather than a number.

    Returns:
        The cell.
    """
    align = "left" if left else "right"
    return (
        f'<td style="text-align: {align}; padding: 4px 14px 4px 0;'
        f' border-bottom: 1px solid #ebebeb;">{escape(value)}</td>'
    )


def _ground(observations: Sequence[Event], cell_km2: float) -> str:
    """Work out how much ground a run of observations covers.

    The cells are unioned rather than added up, so a set that images the same
    patch twice is credited with it once, which is how the search counts
    ground too. That makes this the one column of the table that does not
    double count a revisit.

    Args:
        observations: The observations to measure, from one instrument set.
        cell_km2: How much ground one cell of the feature's grid covers.

    Returns:
        The ground they cover in square kilometres.
    """
    covered: set[int] = set()
    for observation in observations:
        covered.update(packing.cells_of(observation.mask).tolist())
    return quantities.area(len(covered) * cell_km2)


def _pixels(observations: Sequence[Event]) -> float | None:
    """Add up the pixels a run of observations landed inside the feature.

    Args:
        observations: The observations to count, which may predate the
            measurement.

    Returns:
        The total, counting a revisited patch again as the pipeline does, or
        None when any of them was written before pixels were computed.
    """
    counted = [
        observation.pixels
        for observation in observations
        if observation.pixels is not None
    ]
    return sum(counted) if len(counted) == len(observations) else None

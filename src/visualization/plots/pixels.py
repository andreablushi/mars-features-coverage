"""How many pixels each instrument gathered inside the best time window."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import ipywidgets as widgets

from campaign.results import Campaign
from models.results import Event, SetCoverage
from utils import mask as packing
from utils import quantities
from visualization import campaigns, configs, panels
from visualization.selectors.window import Window

_NO_WINDOW = "No stretch of time here holds a sounder track, so there is none to fill."
_UNMEASURED = "not measured"
_HEADINGS = (
    "Instrument",
    "Observations",
    "Pixels in the window",
    "Pixels in the feature",
    "Share of the feature's ground",
)


def plot(coverage: Sequence[SetCoverage], window: Window) -> widgets.Widget:
    """Tabulate what each instrument gathered inside the chosen window.

    A set that took nothing during the window is still given a row, at zero,
    so a missing instrument reads as a measurement rather than as an omission.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        window: The date range the panels are shown over.

    Returns:
        The table as a widget, or the grey panel when there is none to draw.
    """
    if not coverage:
        return panels.unavailable()
    picked = campaigns.picked(coverage, window)
    if picked is None:
        return panels.unavailable(_NO_WINDOW)
    rows = "".join(_row(entry, picked) for entry in coverage)
    return widgets.HTML(
        f"""<div style="font-family: sans-serif; font-size: 13px;">
          <div style="font-weight: 600; margin-bottom: 2px;">
            {escape(panels.title(coverage))}  -  pixels inside the best window
          </div>
          <div style="color: {configs.GREY}; font-size: 12px; font-weight: 600;
                      margin-bottom: 8px;">
            {picked.start:%Y-%m-%d} to {picked.end:%Y-%m-%d},
            {escape(picked.length)}, {picked.observations:,} observations
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
        The heading cell, numbers ranged right as their values are.
    """
    align = "left" if name == "Instrument" else "right"
    return (
        f'<th style="text-align: {align}; padding: 4px 14px 4px 0;'
        f' border-bottom: 1px solid #c4c4c4; font-weight: 600;">{escape(name)}</th>'
    )


def _row(entry: SetCoverage, picked: Campaign) -> str:
    """Build one instrument set's row of the table.

    Args:
        entry: The instrument set the row describes.
        picked: The window its observations are counted inside.

    Returns:
        The row, saying so where the artifacts carry no pixel count at all.
    """
    held = [
        event for event in entry.events if picked.start <= event.t_start <= picked.end
    ]
    inside, total = _pixels(held), entry.summary.pixels
    ground = _ground(held, entry.summary.mask_cells)
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
        f"<tr>{_cell(entry.label, left=True)}"
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


def _ground(events: Sequence[Event], cells: int) -> str:
    """Work out how much of the feature a run of observations covers.

    The cells are unioned rather than added up, so a set that images the same
    patch twice is credited with it once, which is how the search counts ground
    too. That makes this the one column of the table that does not double count
    a revisit.

    Args:
        events: The observations to measure, from one instrument set.
        cells: How many cells of the feature's grid fall inside it.

    Returns:
        The share of the feature they cover, or that it was never measured.
    """
    if not cells:
        return _UNMEASURED
    covered: set[int] = set()
    for event in events:
        covered.update(packing.cells_of(event.mask).tolist())
    return f"{len(covered) / cells:.1%}"


def _pixels(events: Sequence[Event]) -> float | None:
    """Add up the pixels a run of observations landed inside the feature.

    Args:
        events: The observations to count, which may predate the measurement.

    Returns:
        The total, counting a revisited patch again as the pipeline does, or
        None when any of them was written before pixels were computed.
    """
    counted = [event.pixels for event in events if event.pixels is not None]
    return sum(counted) if len(counted) == len(events) else None

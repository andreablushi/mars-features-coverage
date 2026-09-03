"""How much of an instrument a feature swallows, and what lands on one."""

from __future__ import annotations

import math

import ipywidgets as widgets

from analysis.coverage import configs
from analysis.selector.artifacts import filter_config as filtering
from analysis.stats.models.dataset import DatasetStats
from analysis.utils.maths import quantities
from analysis.visualization.common import tables, wording
from analysis.visualization.common.models.tables import Row

_TRACE_KM = configs.SHARAD_ALONG_TRACK_M / 1000.0
_DIAGONAL = math.sqrt(2.0)

_FILLING = (
    "Instrument",
    "Ground one pixel covers",
    "Pixels across a feature",
    "Pixels corner to corner",
    "Pixels to fill a feature",
)
_LANDED = (
    "Instrument",
    "Mean observations offered",
    "Mean pixels landed",
    "Mean pixels landed per observation",
    "Pixels asked",
)


def filling(read: DatasetStats) -> widgets.Widget:
    """Tabulate how much of each instrument it takes to cover a whole feature."""
    # The middling width, since a handful of very wide features would stand for the rest
    feature_km = read.widths.middle
    # To a tenth below ten kilometres and whole above it
    across = f"{feature_km:,.0f} km" if feature_km >= 10.0 else f"{feature_km:,.1f} km"
    rows: list[Row] = []
    for iid in read.iids:
        # The median, since a handful of records publish a pixel far out from the rest
        measured = read.held.pixel_km2[iid]
        ground = measured.middle if measured.counted else 0.0
        if not ground:
            rows.append((iid,) + (wording.UNCOUNTED,) * 4)
            continue
        # A sounder never fills an area, so its pixels are traces along its track
        sounder = iid == wording.SOUNDER
        side = _TRACE_KM if sounder else math.sqrt(ground)
        rows.append(
            (
                iid,
                f"{ground * 1e6:,.0f} m2",
                quantities.compact(feature_km / side),
                quantities.compact(feature_km * _DIAGONAL / side),
                wording.NOTHING
                if sounder
                else quantities.compact(feature_km * feature_km / ground),
            )
        )
    return tables.written(
        f"What it takes to fill a feature {across} across", _FILLING, rows
    )


def landed(read: DatasetStats) -> widgets.Widget:
    """Tabulate what each instrument lands on a feature and what is asked of it."""
    rows: list[Row] = []
    for iid in read.iids:
        asked = filtering.FILTER.admits.get(iid)
        # A sounder counts traces, not picture elements, so its pixels go unmarked
        unit = "" if iid == wording.SOUNDER else " px"
        written = [
            wording.spread(
                measured, lambda pixels: f"{quantities.compact(pixels)}{unit}"
            )
            if measured.counted
            else wording.UNCOUNTED
            for measured in (read.held.landed[iid], read.held.pixels_per_look[iid])
        ]
        rows.append(
            (
                iid,
                wording.spread(read.offered[iid], lambda offered: f"{offered:,.1f}"),
                *written,
                f"{asked:,.0f}" if asked else wording.NOTHING,
            )
        )
    return tables.written("What each instrument lands on a feature", _LANDED, rows)

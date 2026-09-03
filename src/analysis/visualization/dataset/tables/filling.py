"""How much of an instrument a feature swallows, and what lands on one."""

from __future__ import annotations

import math

import ipywidgets as widgets

from analysis.coverage import configs
from analysis.sampling.models.dataset import DatasetStats
from analysis.sampling.models.spread import Spread
from analysis.selector.artifacts import filter_config as filtering
from analysis.utils.maths import quantities
from analysis.visualization.common import tables, wording
from analysis.visualization.common.tables import Row

# The track one of the sounder's traces covers, in kilometres.
_TRACE_KM = configs.SHARAD_ALONG_TRACK_M / 1000.0

# How much further a corner to corner crossing runs than a straight one.
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
    """Tabulate how much of each instrument it takes to cover a whole feature.

    The feature is taken at its middling width, since a handful of very wide ones
    would otherwise stand for the rest, so that width titles the table rather
    than being repeated down it.

    Args:
        read: What the filter made of the features swept.

    Returns:
        The table as a widget.
    """
    feature_km = read.widths.middle if read.widths.counted else 0.0
    # To a tenth below ten kilometres and whole above it
    across = f"{feature_km:,.0f} km" if feature_km >= 10.0 else f"{feature_km:,.1f} km"
    return tables.written(
        f"What it takes to fill a feature {across} across",
        _FILLING,
        [_fills(read, iid, feature_km) for iid in read.iids],
    )


def landed(read: DatasetStats) -> widgets.Widget:
    """Tabulate what each instrument really lands on a feature and what is asked of it.

    Args:
        read: What the filter made of the features swept.

    Returns:
        The table as a widget.
    """
    return tables.written(
        "What each instrument lands on a feature",
        _LANDED,
        [_lands(read, iid) for iid in read.iids],
    )


def _fills(read: DatasetStats, iid: str, feature_km: float) -> Row:
    """Write how much of one instrument it takes to cover a whole feature.

    A sounder never fills an area, so its pixels are traces counted along the
    track it flies and it is credited with no count for filling a feature at all.

    Args:
        read: What the filter made of the features swept.
        iid: The instrument to write.
        feature_km: How wide the middling feature is, in kilometres.

    Returns:
        The row, reading nothing at all where no pixel size is known.
    """
    measured = read.held.pixel_km2.get(iid)
    # The median, since a handful of records publish a pixel orders out from the rest
    ground = measured.middle if measured and measured.counted else 0.0
    if not ground or not feature_km:
        return (iid,) + (wording.UNCOUNTED,) * 4
    sounder = iid == wording.SOUNDER
    across = _TRACE_KM if sounder else math.sqrt(ground)
    return (
        iid,
        f"{ground * 1e6:,.0f} m2",
        quantities.compact(feature_km / across),
        quantities.compact(feature_km * _DIAGONAL / across),
        wording.NOTHING
        if sounder
        else quantities.compact(feature_km * feature_km / ground),
    )


def _lands(read: DatasetStats, iid: str) -> Row:
    """Write what one instrument offers a feature and what the filter asks of it.

    Args:
        read: What the filter made of the features swept.
        iid: The instrument to write.

    Returns:
        Its observations, the pixels it lands, and the bar it clears.
    """
    asked = filtering.FILTER.admits.get(iid)

    # A sounder counts traces, not picture elements, so its pixels go unmarked
    unit = "" if iid == wording.SOUNDER else " px"

    def counted(measured: Spread | None) -> str:
        """Write a pixel count read off many features, in the instrument's own units."""
        if measured is None or not measured.counted:
            return wording.UNCOUNTED
        return wording.spread(
            measured, lambda pixels: f"{quantities.compact(pixels)}{unit}"
        )

    return (
        iid,
        wording.spread(read.offered[iid], lambda offered: f"{offered:,.1f}"),
        counted(read.held.landed.get(iid)),
        counted(read.held.pixels_per_look.get(iid)),
        f"{asked:,.0f}" if asked else wording.NOTHING,
    )

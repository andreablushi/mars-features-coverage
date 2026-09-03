"""The feature on show, with the footprint of every observation it keeps."""

from __future__ import annotations

import ipywidgets as widgets
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

from analysis.stats.feature import reading
from analysis.stats.models.feature import FeatureLooks
from analysis.visualization.common import panels
from analysis.visualization.common.picker import Coverage
from analysis.visualization.feature.plots import mosaic, outlines, placing
from analysis.visualization.feature.plots.placing import Box, Placed

MAP_FIGURE_SIZE = (9.0, 6.0)

# How the feature itself is drawn under the footprints.
FEATURE_EDGE = "#ffffff"
FEATURE_WIDTH = 1.4
TRACE_WIDTH = 1.2
TRACE_ALPHA = 0.85

# How the note is written over a feature with nothing to trace on it.
NOTE_COLOUR = "#ffffff"
NOTE_SIZE = 11

_NOTHING = "No footprints available"


def plot(coverage: Coverage) -> widgets.Widget:
    """Show the feature with the footprint of every observation it keeps.

    Args:
        coverage: The feature on show, as the instrument sets it holds.

    Returns:
        The map as a widget, or the grey panel when there is nothing to crop to.
    """
    if not coverage:
        return panels.unavailable()
    summary = coverage[0].summary
    grid = placing.placed(
        summary.feature_class, summary.feature_name, summary.grid_side
    )
    if grid is None:
        return panels.unavailable(mosaic.BASEMAP_FAILED.format(reason=mosaic.NO_BOX))
    looks = reading.read_feature(coverage)
    box = grid.box()
    title = panels.title(coverage)
    return mosaic.fetched(
        box, lambda image: figure(grid, coverage, looks, box, image, title)
    )


def figure(
    grid: Placed,
    coverage: Coverage,
    looks: FeatureLooks | None,
    box: Box,
    image: bytes,
    title: str,
) -> widgets.Widget:
    """Draw the feature's crop with the footprints its window keeps traced on it.

    Args:
        grid: Where the feature's grid falls on the mosaic.
        coverage: The feature on show, whose published footprints are traced.
        looks: What the selection left on it, or None where it left nothing.
        box: The lon/lat box the crop covers.
        image: The crop as PNG bytes.
        title: The feature, for the line above the map.

    Returns:
        The figure as a widget, carrying the crop alone where there is nothing to trace.
    """
    drawn, axis = panels.board(MAP_FIGURE_SIZE)
    mosaic.draw(axis, box, image)
    lon, lat = grid.outline()
    axis.plot(lon, lat, color=FEATURE_EDGE, linewidth=FEATURE_WIDTH)
    colours = _traces(axis, grid, coverage, looks)
    if not colours:
        panels.note(axis, _NOTHING, colour=NOTE_COLOUR, size=NOTE_SIZE)
    axis.set_title(title, fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    panels.key_beside(
        drawn,
        [
            Line2D([], [], color=colour, linewidth=TRACE_WIDTH, label=label)
            for label, colour in colours.items()
        ],
    )
    return panels.rendered(drawn)


def _traces(
    axis: Axes, grid: Placed, coverage: Coverage, looks: FeatureLooks | None
) -> dict[str, panels.Colour]:
    """Trace the footprint of every observation the feature keeps.

    Args:
        axis: The panel to draw on.
        grid: Where the feature's grid falls on the mosaic.
        coverage: The feature on show, whose published footprints are read.
        looks: What the selection left on it, or None where it left nothing.

    Returns:
        The colour each instrument set was drawn in, by set label.
    """
    if looks is None or not looks.window.kept:
        return {}
    track = looks.track
    shapes = outlines.read(coverage)
    colours = panels.colours(track.labels)
    drawn: dict[str, panels.Colour] = {}
    for index in looks.taken:
        shape = shapes.get(track.observations[index].pdsid)
        if shape is None:
            continue
        label = track.labels[track.owners[index]]
        for lon, lat in outlines.traced(shape):
            axis.plot(
                grid.around(lon),
                lat,
                color=colours[label],
                linewidth=TRACE_WIDTH,
                alpha=TRACE_ALPHA,
            )
            drawn[label] = colours[label]
    return drawn

"""The feature on show, with the footprint of every observation it keeps."""

from __future__ import annotations

import ipywidgets as widgets
from matplotlib.lines import Line2D

from analysis.stats.feature import read
from analysis.stats.models.feature import FeatureLooks
from analysis.visualization.common import panels
from analysis.visualization.common.models.colours import Colour
from analysis.visualization.common.models.coverage import Coverage
from analysis.visualization.feature.models.placing import Box, Placed
from analysis.visualization.feature.plots import mosaic, outlines, placing

MAP_FIGURE_SIZE = (9.0, 6.0)

FEATURE_EDGE = "#ffffff"
FEATURE_WIDTH = 1.4
TRACE_WIDTH = 1.2
TRACE_ALPHA = 0.85

NOTE_COLOUR = "#ffffff"
NOTE_SIZE = 11

_NOTHING = "No footprints available"


def plot(coverage: Coverage) -> widgets.Widget:
    """Show the feature with the footprint of every observation it keeps."""
    if not coverage:
        return panels.unavailable()
    summary = coverage[0].summary
    grid = placing.placed(
        summary.feature_class, summary.feature_name, summary.grid_side
    )
    if grid is None:
        return panels.unavailable(mosaic.BASEMAP_FAILED.format(reason=mosaic.NO_BOX))
    looks = read.read_feature(coverage)
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
    """Draw the feature's crop with the footprints its window keeps traced on it."""
    drawn, axis = panels.board(MAP_FIGURE_SIZE)
    mosaic.draw(axis, box, image)
    lon, lat = grid.outline()
    axis.plot(lon, lat, color=FEATURE_EDGE, linewidth=FEATURE_WIDTH)
    traced: dict[str, Colour] = {}
    if looks is not None and looks.window.kept:
        track = looks.track
        shapes = outlines.read(coverage)
        colours = panels.colours(track.labels)
        for index in looks.taken:
            shape = shapes[track.observations[index].pdsid]
            label = track.labels[track.owners[index]]
            for line_lon, line_lat in outlines.traced(shape):
                axis.plot(
                    grid.around(line_lon),
                    line_lat,
                    color=colours[label],
                    linewidth=TRACE_WIDTH,
                    alpha=TRACE_ALPHA,
                )
                traced[label] = colours[label]
    if not traced:
        panels.note(axis, _NOTHING, colour=NOTE_COLOUR, size=NOTE_SIZE)
    axis.set_title(title, fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    panels.key_beside(
        drawn,
        [
            Line2D([], [], color=colour, linewidth=TRACE_WIDTH, label=label)
            for label, colour in traced.items()
        ],
    )
    return panels.rendered(drawn)

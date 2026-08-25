"""The tile on show, with the footprint every observation its window keeps left."""

from __future__ import annotations

import threading

import ipywidgets as widgets
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

from visualization.common import panels, series
from visualization.feature import picker
from visualization.feature.picker import TileView
from visualization.feature.plots import basemap, outlines, overlay
from visualization.feature.plots.overlay import Box, Placed

MAP_FIGURE_SIZE = (9.0, 6.0)

# How the tile itself is drawn under the footprints.
TILE_EDGE = "#ffffff"
TILE_WIDTH = 1.4
TRACE_WIDTH = 1.2
TRACE_ALPHA = 0.85

_NO_WINDOW = "This tile holds no window worth keeping, so nothing is drawn."
_UNKNOWN = "this feature has no lon/lat box to crop the mosaic to"
_UNPUBLISHED = "The footprints of this feature are no longer on disk."


def plot(chosen: TileView | None) -> widgets.Widget:
    """Show the tile with the footprints the observations its window keeps left.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The map as a widget, or the grey panel when there is none to draw.
    """
    if chosen is None:
        return panels.unavailable(picker.NO_TILE)
    if chosen.survey is None:
        return panels.unavailable(_NO_WINDOW)
    summary = chosen.view.coverage[0].summary
    grid = overlay.placed(
        summary.feature_class,
        summary.feature_name,
        summary.grid_side,
        chosen.across,
    )
    if grid is None:
        return panels.unavailable(overlay.BASEMAP_FAILED.format(reason=_UNKNOWN))
    space = widgets.Box([_loading()])
    threading.Thread(target=_fill, args=(space, grid, chosen), daemon=True).start()
    return space


def _loading() -> widgets.HTML:
    """Set the note shown while the crop is fetched.

    Returns:
        The note.
    """
    return widgets.HTML(
        f"<div style='color: {panels.GREY}; font-family: sans-serif;"
        f" font-size: 12px; padding: 12px;'>{overlay.BASEMAP_LOADING}</div>"
    )


def _fill(space: widgets.Box, grid: Placed, chosen: TileView) -> None:
    """Put the fetched map in the space claimed for it.

    Args:
        space: The claimed space, already on screen.
        grid: Where the feature's grid falls on the mosaic.
        chosen: The tile on show.

    Returns:
        None.
    """
    stats = chosen.stats
    box = grid.tile_box(stats.row, stats.column)
    try:
        image = overlay.crop(box)
    except Exception as exc:
        space.children = (
            panels.unavailable(overlay.BASEMAP_FAILED.format(reason=exc)),
        )
        return
    space.children = (_figure(grid, chosen, box, image),)


def _figure(grid: Placed, chosen: TileView, box: Box, image: bytes) -> widgets.Widget:
    """Draw the tile's crop with the footprints its window keeps traced on it.

    Args:
        grid: Where the feature's grid falls on the mosaic.
        chosen: The tile on show.
        box: The lon/lat box the crop covers.
        image: The crop as PNG bytes.

    Returns:
        The figure as a widget, or the grey panel when the footprints were
        discarded once the feature was measured.
    """
    shapes = outlines.read(chosen.view.coverage)
    if not shapes:
        return panels.unavailable(_UNPUBLISHED)
    figure, axis = panels.board(MAP_FIGURE_SIZE)
    basemap.mosaic(axis, box, image)
    lon, lat = grid.tile(chosen.stats.row, chosen.stats.column)
    axis.plot(lon, lat, color=TILE_EDGE, linewidth=TILE_WIDTH)
    colours = _traces(axis, grid, chosen, shapes)
    axis.set_title(chosen.name, fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    panels.key_beside(
        figure,
        [
            Line2D([], [], color=colour, linewidth=TRACE_WIDTH, label=label)
            for label, colour in colours.items()
        ],
    )
    return panels.rendered(figure)


def _traces(
    axis: Axes, grid: Placed, chosen: TileView, shapes: dict
) -> dict[str, tuple]:
    """Trace the footprint of every observation the tile's window keeps.

    Args:
        axis: The panel to draw on.
        grid: Where the feature's grid falls on the mosaic, which the
            longitudes are brought onto the turn of.
        chosen: The tile on show.
        shapes: The published footprint of each observation, by product id.

    Returns:
        The colour each instrument set was drawn in, by set label, for the
        key beside the map.
    """
    track = chosen.track
    colours = panels.colours(series.over_tile(track))
    drawn: dict[str, tuple] = {}
    for index in chosen.survey.kept:
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

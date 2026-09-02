"""The feature itself: the ground it covers, and what the search made of it."""

from __future__ import annotations

from html import escape

import ipywidgets as widgets
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch

from analysis.sampling.models.study import Study
from analysis.visualization.common import panels, surveys
from analysis.visualization.common.picker import View
from analysis.visualization.feature.plots import mosaic, placing
from analysis.visualization.feature.plots.placing import Box, Placed

MAP_FIGURE_SIZE = (7.0, 6.0)

# How wide the report beside the map is set, so the map keeps the rest.
REPORT_WIDTH = "360px"

# How the feature is drawn, by what the search made of it.
FEATURE_FILL = 0.18
FEATURE_WIDTH = 1.4
FEATURE_COLOURS = (
    (True, panels.KEPT, "feature kept"),
    (False, panels.REFUSED, "feature refused"),
)


def plot(view: View) -> widgets.Widget:
    """Show the ground the feature covers, marked by what the search made of it.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The report beside the mosaic, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    summary = view.coverage[0].summary
    study = surveys.studied(view.coverage, view.strategy)
    grid = placing.placed(
        summary.feature_class, summary.feature_name, summary.grid_side
    )
    if grid is None:
        return panels.unavailable(mosaic.BASEMAP_FAILED.format(reason=mosaic.NO_BOX))
    title = panels.title(view.coverage)
    box = grid.box()
    return widgets.HBox(
        [
            _report(view, study, box),
            mosaic.fetched(box, lambda image: figure(grid, study, box, image, title)),
        ],
        layout=widgets.Layout(
            align_items="flex-start", flex_flow="row nowrap", grid_gap="24px"
        ),
    )


def figure(
    grid: Placed, study: Study, box: Box, image: bytes, title: str
) -> widgets.Image:
    """Draw the mosaic with the feature laid over it.

    Args:
        grid: Where the feature's grid falls on the mosaic.
        study: What the search found over it.
        box: The lon/lat box the crop covers.
        image: The crop as PNG bytes.
        title: The feature, for the line above the map.

    Returns:
        The figure as a widget.
    """
    drawn, axis = panels.board(MAP_FIGURE_SIZE)
    mosaic.draw(axis, box, image)
    _feature(axis, grid, study.survey is not None)
    axis.set_title(title, fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    panels.key_below(
        drawn,
        [
            Patch(edgecolor=colour, facecolor=to_rgba(colour, FEATURE_FILL), label=said)
            for _, colour, said in FEATURE_COLOURS
        ],
    )
    return panels.rendered(drawn)


def _report(view: View, study: Study, box: Box) -> widgets.HTML:
    """Report the feature's extent, its window, and what each set holds of it.

    Args:
        view: The feature on show and the strategy it is judged under.
        study: What the search found over it.
        box: The lon/lat box its grid falls in.

    Returns:
        The report.
    """
    summary = view.coverage[0].summary
    body = escape(
        "\n".join(
            f"{instrument.label:16s} {instrument.summary.n_obs:6,d} observations"
            f"{f'  ({instrument.reason})' if instrument.reason else ''}"
            for instrument in view.coverage
        )
    )
    return widgets.HTML(
        f"<b>{escape(panels.title(view.coverage))}</b><br>"
        f"{summary.feature_area_km2:,.1f} km2 bounding box, "
        f"{box.south:.3f} to {box.north:.3f} lat, "
        f"{box.west:.3f} to {box.east:.3f} lon<br>"
        f"{escape(view.strategy.name)}: {_verdict(study)}"
        f"<pre style='margin: 8px 0 0; line-height: 1.4'>{body}</pre>",
        layout=widgets.Layout(flex=f"0 0 {REPORT_WIDTH}"),
    )


def _verdict(study: Study) -> str:
    """Say what the search made of the feature.

    Args:
        study: What it found over it.

    Returns:
        The window it earned, or that it earned none.
    """
    if study.survey is None:
        return "no window worth keeping"
    survey = study.survey
    return f"{survey.start:%Y-%m-%d} to {survey.end:%Y-%m-%d}, {survey.days:,.0f} days"


def _feature(axis: Axes, grid: Placed, kept: bool) -> None:
    """Shade and outline the feature, marked by what the search made of it.

    Args:
        axis: The panel to draw on.
        grid: Where the feature's grid falls on the mosaic.
        kept: Whether it earned a window worth keeping.

    Returns:
        None.
    """
    colour = panels.KEPT if kept else panels.REFUSED
    lon, lat = grid.outline()
    ring = np.column_stack([lon, lat])
    axis.fill(ring[:, 0], ring[:, 1], color=colour, alpha=FEATURE_FILL, zorder=2)
    axis.plot(ring[:, 0], ring[:, 1], color=colour, linewidth=FEATURE_WIDTH, zorder=3)

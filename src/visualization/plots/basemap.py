"""The feature itself: the ground it covers, and what it looks like from orbit."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from functools import lru_cache
from html import escape

import httpx
import ipywidgets as widgets

from analysis.utils import geodesy
from models.feature import Feature
from models.results import SetCoverage
from storage import catalog
from utils.slugify import slugify
from visualization import panels

# The global mosaic a feature is drawn on, served as WMS by the USGS.
BASEMAP_URL = "https://planetarymaps.usgs.gov/cgi-bin/mapserv"
BASEMAP_MAP = "/maps/mars/mars_simp_cyl.map"
BASEMAP_LAYER = "THEMIS"
BASEMAP_PIXELS = 700
BASEMAP_WIDTH = "300px"
BASEMAP_TIMEOUT = 30.0
BASEMAP_FAILED = "The basemap could not be fetched: {reason}"
BASEMAP_LOADING = "Fetching the basemap..."
BASEMAP_CACHE = 32

# The least ground a side of the crop covers, however thin the box is.
BASEMAP_MIN_SPAN_DEG = 0.5


def plot(coverage: Sequence[SetCoverage], _window=None) -> widgets.Widget:
    """Show how much ground the feature covers, and a view of it.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        _window: The date range, ignored: the ground does not move.

    Returns:
        The report beside the basemap view, or the grey panel when nothing is
        loaded.
    """
    if not coverage:
        return panels.unavailable()
    summary = coverage[0].summary
    feature = _feature(summary.feature_class, summary.feature_name)
    if feature is None:
        return panels.unavailable(BASEMAP_FAILED.format(reason="unknown box"))
    return widgets.HBox(
        [_report(coverage, feature), _view(feature)],
        layout=widgets.Layout(align_items="flex-start", grid_gap="24px"),
    )


def _report(coverage: Sequence[SetCoverage], feature: Feature) -> widgets.HTML:
    """Report the feature's extent and what each instrument set holds of it.

    Args:
        coverage: The feature's instrument sets, widest coverage first.
        feature: The catalogued feature, carrying its lat/lon box.

    Returns:
        The report.
    """
    area_km2 = coverage[0].summary.feature_area_km2
    lat = f"{feature.min_lat:.3f} to {feature.max_lat:.3f} lat"
    lon = f"{feature.west_lon:.3f} to {feature.east_lon:.3f} lon"
    body = escape(
        "\n".join(
            f"{entry.label:16s} {entry.summary.n_obs:6,d} observations"
            f"{f'  ({entry.reason})' if entry.reason else ''}"
            for entry in coverage
        )
    )
    return widgets.HTML(
        f"<b>{panels.title(coverage)}</b><br>"
        f"{area_km2:,.1f} km2 bounding box, {lat}, {lon}"
        f"<pre style='margin: 8px 0 0; line-height: 1.4'>{body}</pre>"
    )


def _view(feature: Feature) -> widgets.Widget:
    """Claim the space the basemap goes in and fetch it off the redraw.

    The fetch crosses the network, so it runs on its own thread and fills the
    space in when it lands. The rest of the panel is drawn and read meanwhile.

    Args:
        feature: The feature to crop the view to.

    Returns:
        A box holding the loading note, which the fetch replaces.
    """
    box = widgets.Box([_placeholder(BASEMAP_LOADING)])
    threading.Thread(target=_fill, args=(box, feature), daemon=True).start()
    return box


def _fill(box: widgets.Box, feature: Feature) -> None:
    """Put the fetched view in the space claimed for it.

    Args:
        box: The claimed space, already on screen.
        feature: The feature to crop the view to.

    Returns:
        None.
    """
    window = _window(feature)
    try:
        image = _fetch(window, _pixels(window))
    except Exception as exc:
        box.children = (_placeholder(BASEMAP_FAILED.format(reason=exc)),)
        return
    box.children = (
        widgets.Image(
            value=image,
            format="png",
            layout=widgets.Layout(max_width=BASEMAP_WIDTH, max_height=BASEMAP_WIDTH),
        ),
    )


def _placeholder(text: str) -> widgets.HTML:
    """Set a note in the space the image will fill.

    Args:
        text: The line to set.

    Returns:
        The note, squared off to the space the crop is fitted into.
    """
    return widgets.HTML(
        f"<div style='width: {BASEMAP_WIDTH};"
        f" height: {BASEMAP_WIDTH};"
        f" display: flex; align-items: center; justify-content: center;"
        f" box-sizing: border-box; padding: 10px; text-align: center;"
        f" background: #f2f2f2; border: 1px solid #d8d8d8; border-radius: 4px;"
        f" color: {panels.GREY}; font-family: sans-serif; font-size: 12px;'>"
        f"{escape(text)}</div>"
    )


def _window(feature: Feature) -> tuple[float, float, float, float]:
    """Return the lon/lat box to crop the view to.

    Args:
        feature: The feature to crop to.

    Returns:
        The west, south, east, and north bounds to draw.
    """
    centre_lat = (feature.min_lat + feature.max_lat) / 2.0
    floor = BASEMAP_MIN_SPAN_DEG
    south, north = _floored(feature.min_lat, feature.max_lat, floor)
    start = float(geodesy.normalise_longitude(feature.west_lon))
    west, east = _floored(
        start, start + _span(feature), floor / geodesy.longitude_stretch(centre_lat)
    )
    if west < -180.0:
        west, east = west + 360.0, east + 360.0
    return west, south, east, north


def _span(feature: Feature) -> float:
    """Return how far east a feature's box runs, in degrees.

    Args:
        feature: The catalogued feature.

    Returns:
        The eastward span: zero for a feature the catalogue gives no extent at
        all, and a whole turn for one that circles a pole.
    """
    if feature.is_point:
        return 0.0
    return geodesy.longitude_span(feature.west_lon, feature.east_lon)


def _floored(low: float, high: float, minimum: float) -> tuple[float, float]:
    """Hold a side of the box open to a minimum width.

    Args:
        low: The lower bound in degrees.
        high: The upper bound in degrees.
        minimum: The least the side may span.

    Returns:
        The bounds, moved apart about their middle when they fall too close.
    """
    if high - low >= minimum:
        return low, high
    centre = (low + high) / 2.0
    return centre - minimum / 2.0, centre + minimum / 2.0


def _pixels(window: tuple[float, float, float, float]) -> tuple[int, int]:
    """Return the image size to ask for so the crop is not stretched.

    Args:
        window: The west, south, east, and north bounds to draw.

    Returns:
        The width and height in pixels, neither below one.
    """
    west, south, east, north = window
    tall = north - south
    wide = (east - west) * geodesy.longitude_stretch((south + north) / 2.0)
    longest = max(wide, tall)
    return (
        max(1, round(BASEMAP_PIXELS * wide / longest)),
        max(1, round(BASEMAP_PIXELS * tall / longest)),
    )


@lru_cache(maxsize=BASEMAP_CACHE)
def _fetch(window: tuple[float, float, float, float], size: tuple[int, int]) -> bytes:
    """Fetch one basemap view.

    Args:
        window: The west, south, east, and north bounds to draw.
        size: The width and height to draw them at, in pixels.

    Returns:
        The image as PNG bytes.

    Raises:
        ValueError: When the service answers with anything but an image, which
            it does with a 200 and an XML report when a request is malformed.
    """
    response = httpx.get(
        BASEMAP_URL,
        params={
            "map": BASEMAP_MAP,
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": BASEMAP_LAYER,
            "STYLES": "",
            "SRS": "EPSG:4326",
            "BBOX": ",".join(f"{bound:.4f}" for bound in window),
            "WIDTH": size[0],
            "HEIGHT": size[1],
            "FORMAT": "image/png",
        },
        timeout=BASEMAP_TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise ValueError(response.text.strip()[:200])
    return response.content


@lru_cache(maxsize=1)
def _catalogue() -> dict[tuple[str, str], Feature]:
    """Read the feature catalogue once, keyed by the slugs the trees use.

    Returns:
        Every catalogued feature, by class and name slug.
    """
    return {
        (slugify(feature.feature_class), slugify(feature.name)): feature
        for feature in catalog.read_features()
    }


def _feature(feature_class: str, name: str) -> Feature | None:
    """Find one catalogued feature's lat/lon box.

    Args:
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.

    Returns:
        The catalogued feature, or None when the catalogue does not hold it.
    """
    return _catalogue().get((slugify(feature_class), slugify(name)))

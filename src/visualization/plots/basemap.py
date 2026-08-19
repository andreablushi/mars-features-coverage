"""The feature itself: the ground it covers, and what it looks like from orbit."""

from __future__ import annotations

import math
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
from visualization import configs, panels


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
        return panels.unavailable(configs.BASEMAP_FAILED.format(reason="unknown box"))
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
        feature: The feature to centre the view on.

    Returns:
        A box holding the loading note, which the fetch replaces.
    """
    box = widgets.Box([_placeholder(configs.BASEMAP_LOADING)])
    threading.Thread(target=_fill, args=(box, feature), daemon=True).start()
    return box


def _fill(box: widgets.Box, feature: Feature) -> None:
    """Put the fetched view in the space claimed for it.

    Args:
        box: The claimed space, already on screen.
        feature: The feature to centre the view on.

    Returns:
        None.
    """
    try:
        image = _fetch(_window(feature))
    except Exception as exc:
        box.children = (_placeholder(configs.BASEMAP_FAILED.format(reason=exc)),)
        return
    box.children = (
        widgets.Image(
            value=image,
            format="png",
            layout=widgets.Layout(width=configs.BASEMAP_WIDTH, height="auto"),
        ),
    )


def _placeholder(text: str) -> widgets.HTML:
    """Set a note in the space the image will fill.

    Args:
        text: The line to set.

    Returns:
        The note, squared off to the image's own size so nothing jumps when the
        fetch lands.
    """
    return widgets.HTML(
        f"<div style='width: {configs.BASEMAP_WIDTH};"
        f" height: {configs.BASEMAP_WIDTH};"
        f" display: flex; align-items: center; justify-content: center;"
        f" box-sizing: border-box; padding: 10px; text-align: center;"
        f" background: #f2f2f2; border: 1px solid #d8d8d8; border-radius: 4px;"
        f" color: {configs.GREY}; font-family: sans-serif; font-size: 12px;'>"
        f"{escape(text)}</div>"
    )


def _window(feature: Feature) -> tuple[float, float, float, float]:
    """Return the lon/lat box to draw around a feature.

    Args:
        feature: The feature to centre the view on.

    Returns:
        The west, south, east, and north bounds, inside the globe.
    """
    centre_lat = (feature.min_lat + feature.max_lat) / 2.0
    shrink = max(math.cos(math.radians(centre_lat)), 0.05)
    if feature.has_longitude_extent:
        centre_lon = geodesy.bbox_centre(
            feature.min_lat, feature.max_lat, feature.west_lon, feature.east_lon
        )[0]
        width = geodesy.longitude_span(feature.west_lon, feature.east_lon) * shrink
    else:
        centre_lon, width = feature.west_lon, 0.0
    span = max(feature.max_lat - feature.min_lat, width, configs.BASEMAP_MIN_SPAN_DEG)
    half_lat = span * configs.BASEMAP_PADDING / 2.0
    half_lon = half_lat / shrink
    south, north = _fit(centre_lat, half_lat, 90.0)
    west, east = _fit(float(geodesy.normalise_longitude(centre_lon)), half_lon, 180.0)
    return west, south, east, north


def _fit(centre: float, half: float, limit: float) -> tuple[float, float]:
    """Centre a span on an axis without leaving the globe.

    Args:
        centre: The middle of the span in degrees.
        half: Half its width in degrees.
        limit: The furthest the axis reaches from zero.

    Returns:
        The low and high bounds, shifted inwards when they would overhang.
    """
    half = min(half, limit)
    low = max(-limit, min(centre - half, limit - 2 * half))
    return low, low + 2 * half


@lru_cache(maxsize=configs.BASEMAP_CACHE)
def _fetch(window: tuple[float, float, float, float]) -> bytes:
    """Fetch one basemap view.

    Args:
        window: The west, south, east, and north bounds to draw.

    Returns:
        The image as PNG bytes.

    Raises:
        ValueError: When the service answers with anything but an image, which
            it does with a 200 and an XML report when a request is malformed.
    """
    response = httpx.get(
        configs.BASEMAP_URL,
        params={
            "map": configs.BASEMAP_MAP,
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": configs.BASEMAP_LAYER,
            "STYLES": "",
            "SRS": "EPSG:4326",
            "BBOX": ",".join(f"{bound:.4f}" for bound in window),
            "WIDTH": configs.BASEMAP_PIXELS,
            "HEIGHT": configs.BASEMAP_PIXELS,
            "FORMAT": "image/png",
        },
        timeout=configs.BASEMAP_TIMEOUT,
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

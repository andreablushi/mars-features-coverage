"""The feature itself: the ground it covers, and what it looks like from orbit.

The picture is pulled from the USGS Mars basemap when the panel is drawn and
kept in memory only, so looking at a feature never adds anything to the data on
disk. A view that has already been fetched is reused, which is what keeps
flipping between two features from asking twice.

The area is the feature's bounding box, not its true outline, because the box
is the whole the coverage numbers are shares of and the catalogue carries
nothing finer.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache

import httpx
import ipywidgets as widgets

from analysis.computation import geodesy
from analysis.models.coverage import SetCoverage
from common.files import slugify
from download.models.feature import Feature
from download.storage import cache
from visualization import configs, panels


def plot(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Show how much ground the feature covers, and a view of it.

    Args:
        coverage: The feature's instrument sets, widest coverage first.

    Returns:
        The measurements above the basemap view, or the grey panel when
        nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    summary = coverage[0].summary
    feature = _feature(summary.feature_class, summary.feature_name)
    if feature is None:
        return panels.unavailable(configs.BASEMAP_FAILED.format(reason="unknown box"))
    return widgets.VBox([_measurements(coverage, feature), _view(feature)])


def _measurements(coverage: Sequence[SetCoverage], feature: Feature) -> widgets.HTML:
    """Report the feature's extent and the ground its box covers.

    Args:
        coverage: The feature's instrument sets, carrying the measured area.
        feature: The catalogued feature, carrying its lat/lon box.

    Returns:
        The report.
    """
    area_km2 = coverage[0].summary.feature_area_km2
    lat = f"{feature.min_lat:.3f} to {feature.max_lat:.3f} lat"
    lon = f"{feature.west_lon:.3f} to {feature.east_lon:.3f} lon"
    return widgets.HTML(
        f"<b>{panels.title(coverage)}</b><br>"
        f"{area_km2:,.1f} km2 bounding box, {lat}, {lon}"
    )


def _view(feature: Feature) -> widgets.Widget:
    """Fetch the basemap around a feature.

    Args:
        feature: The feature to centre the view on.

    Returns:
        The image, or the grey panel explaining why it could not be fetched.
    """
    try:
        image = _fetch(_window(feature))
    except Exception as exc:
        return panels.unavailable(configs.BASEMAP_FAILED.format(reason=exc))
    return widgets.Image(
        value=image,
        format="png",
        layout=widgets.Layout(max_width="100%", height="auto"),
    )


def _window(feature: Feature) -> tuple[float, float, float, float]:
    """Return the lon/lat box to draw around a feature.

    The view is widened so the feature sits in context rather than filling the
    frame. Longitudes are measured against latitude on the way in and stretched
    back on the way out, because a degree of longitude covers less ground the
    further from the equator it sits, so comparing the two spans raw would
    frame a polar feature as if it were far wider than it is.

    Args:
        feature: The feature to centre the view on.

    Returns:
        The west, south, east, and north bounds, inside the globe.
    """
    centre_lon, centre_lat = geodesy.bbox_centre(
        feature.min_lat, feature.max_lat, feature.west_lon, feature.east_lon
    )
    shrink = max(math.cos(math.radians(centre_lat)), 0.05)
    span = max(
        feature.max_lat - feature.min_lat,
        geodesy.longitude_span(feature.west_lon, feature.east_lon) * shrink,
        configs.BASEMAP_MIN_SPAN_DEG,
    )
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


@lru_cache(maxsize=32)
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
        for feature in cache.read_features()
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

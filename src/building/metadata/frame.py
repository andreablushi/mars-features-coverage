"""Building one feature's local frame from the box the catalogue gives it."""

from __future__ import annotations

import numpy as np

from building.metadata.models.feature import FeatureFrame
from utils.geometry import geodesy


def feature_frame(feature) -> FeatureFrame:
    """Return the local frame one feature's observations are placed in.

    Args:
        feature: The catalogued feature, carrying the box ODE gives it.

    Returns:
        The frame, centred on the box and carrying how far the box reaches
        from that centre.
    """
    centre_lon, centre_lat = geodesy.bbox_centre(
        feature.min_lat, feature.max_lat, feature.west_lon, feature.east_lon
    )
    # The corners rather than the edges, since the box reaches furthest at them.
    span = geodesy.longitude_span(feature.west_lon, feature.east_lon)
    lons = np.array([feature.west_lon, feature.west_lon + span])
    lats = np.array([feature.min_lat, feature.max_lat])
    east, north = geodesy.laea_forward(*np.meshgrid(lons, lats), centre_lon, centre_lat)
    return FeatureFrame(
        feature_class=feature.feature_class,
        feature_name=feature.name,
        centre_lon=centre_lon,
        centre_lat=centre_lat,
        min_lat=feature.min_lat,
        max_lat=feature.max_lat,
        west_lon=feature.west_lon,
        east_lon=feature.east_lon,
        east_m=float(np.abs(east).max()),
        north_m=float(np.abs(north).max()),
    )

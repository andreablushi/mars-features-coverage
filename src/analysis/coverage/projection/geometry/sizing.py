"""How big an observation is on the ground: its swath, and its pixel."""

from __future__ import annotations

import math

from analysis.coverage import configs


def track_width(track_length_m: float, duration_s: float) -> float:
    """Solve one track's swath width from the speed its ground trace implies.

    Args:
        track_length_m: The ground length of the track in metres, above zero.
        duration_s: The elapsed observation time in seconds, above zero.

    Returns:
        The cross-track width in metres.
    """
    speed = track_length_m / duration_s
    radius = (configs.MARS_GM * configs.MARS_RADIUS_M**2 / speed**2) ** (1.0 / 3.0)
    altitude = radius - configs.MARS_RADIUS_M
    return 2.0 * math.sqrt(configs.SHARAD_WAVELENGTH_M * altitude / 2.0)


def ground_pixel_km2(
    set_key: str, map_scale_m: float | None, width_km: float | None
) -> float:
    """Return the ground one pixel of an observation covers.

    Args:
        set_key: The instrument set the observation was asked for by.
        map_scale_m: The ground size of one pixel, or None to use the configured one.
        width_km: The swath width, set only for a sounder's track.

    Returns:
        The ground one pixel covers in square kilometres.

    Raises:
        KeyError: When a set publishes no scale and none is configured for it.
    """
    if width_km is not None:
        return width_km * configs.SHARAD_ALONG_TRACK_M / 1000.0
    scale = map_scale_m or configs.FALLBACK_PIXEL_M.get(set_key)
    if scale is None:
        raise KeyError(
            f"{set_key} publishes no map scale and none is configured for it, "
            f"so it needs an entry in FALLBACK_PIXEL_M spelled exactly this way"
        )
    return (scale / 1000.0) ** 2

"""How much ground one pixel of an observation covers."""

from __future__ import annotations

from analysis import configs


def ground_pixel_km2(
    set_key: str, map_scale_m: float | None, width_km: float | None
) -> float:
    """Return the ground one pixel of an observation covers.

    Args:
        set_key: The instrument set the observation was asked for by, which
            names the observing mode when a run narrowed a product type to it.
        map_scale_m: The ground size of one pixel, or None when unpublished,
            in which case the size configured for the set is used.
        width_km: The swath width, set only for a sounder's track.

    Returns:
        The ground one pixel covers in square kilometres.

    Raises:
        KeyError: When a set publishes no scale and none is configured for it.
    """
    if width_km is not None:
        return width_km * configs.SHARAD_ALONG_TRACK_M / 1000.0
    scale = map_scale_m or configs.FALLBACK_PIXEL_M[set_key]
    return (scale / 1000.0) ** 2

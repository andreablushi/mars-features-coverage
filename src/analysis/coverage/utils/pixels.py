"""How much ground one pixel of an observation covers."""

from __future__ import annotations

from analysis.coverage import configs


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

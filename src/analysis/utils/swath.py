"""Cross-track swath width for SHARAD, derived per observation."""

from __future__ import annotations

import math

from analysis import configs


def track_width(track_length_m: float, duration_s: float) -> float:
    """Solve one track's swath width from the speed its ground trace implies.

    A circular orbit traces the ground at v = sqrt(GM / r) * R / r, so the
    orbital radius follows from the observed speed as r = (GM * R^2 / v^2)^(1/3),
    and the width is the first Fresnel zone at the altitude that leaves.

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

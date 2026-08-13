"""Cross-track swath width for SHARAD, derived per observation.

ODE models a SHARAD product as a bare line across the surface and publishes no
width for it, so an areal coverage needs one from somewhere. Rather than
assume a constant, each track supplies its own: its ground length divided by
its duration is the ground-track speed, a circular orbit turns that speed into
a spacecraft altitude, and the altitude gives the first Fresnel zone, which is
the pulse-limited cross-track footprint of a nadir sounder.

The only constants involved are published physical facts, the SHARAD centre
frequency and Mars' mass and radius, rather than a fitted swath value.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from analysis import configs

DERIVED = "derived"
FALLBACK = "fallback"


def orbital_altitude(track_length_m: float, duration_s: float) -> float | None:
    """Solve the spacecraft altitude implied by a ground-track speed.

    A circular orbit sweeps its ground track at v = R * sqrt(GM / r**3), which
    inverts to r = (GM * R**2 / v**2) ** (1/3).

    Args:
        track_length_m: The ground length of the track in metres.
        duration_s: The elapsed observation time in seconds.

    Returns:
        The altitude above the mean radius in metres, or None when the inputs
        are unusable or the result falls outside MRO's known orbit band.
    """
    if track_length_m <= 0.0 or duration_s <= 0.0:
        return None
    speed = track_length_m / duration_s
    radius = (configs.MARS_GM * configs.MARS_RADIUS_M**2 / speed**2) ** (1.0 / 3.0)
    altitude = radius - configs.MARS_RADIUS_M
    if not configs.SHARAD_MIN_ALTITUDE_M <= altitude <= configs.SHARAD_MAX_ALTITUDE_M:
        return None
    return altitude


def fresnel_width(altitude_m: float) -> float:
    """Return the first Fresnel zone diameter for a nadir sounder.

    Args:
        altitude_m: The spacecraft altitude above the surface in metres.

    Returns:
        The cross-track footprint width in metres.
    """
    return 2.0 * math.sqrt(configs.SHARAD_WAVELENGTH_M * altitude_m / 2.0)


def resolve_widths(
    measurements: Sequence[tuple[float, float]],
) -> list[tuple[float, str]]:
    """Derive a swath width for every track, filling in the ones that fail.

    A track whose altitude does not solve takes the median width of the tracks
    alongside it that did, and if none of them solved, the width at the nominal
    altitude. Each width carries the label of where it came from so a fallback
    can be filtered out downstream.

    Args:
        measurements: One (track length in metres, duration in seconds) pair
            per track, in the order the widths should be returned.

    Returns:
        One (width in metres, source label) pair per track.
    """
    derived = [
        fresnel_width(altitude) if (altitude := orbital_altitude(*m)) else None
        for m in measurements
    ]
    solved = [width for width in derived if width is not None]
    default = (
        statistics.median(solved)
        if solved
        else fresnel_width(configs.SHARAD_NOMINAL_ALTITUDE_M)
    )
    return [(w, DERIVED) if w is not None else (default, FALLBACK) for w in derived]

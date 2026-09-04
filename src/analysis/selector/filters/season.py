"""How far round its own year Mars had turned, which is what a window is held to."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime

# The Julian date the Unix epoch falls on, which every timestamp is counted from
_JD_UNIX_EPOCH = 2440587.5

# Seconds in a day, which the Julian date below is counted in
_DAY_SECONDS = 86400.0

# The Julian date of the J2000 epoch the series below is written against
_J2000 = 2451545.0


def arcs(when: Sequence[datetime]) -> list[float]:
    """Say how far round its orbit Mars had come as each observation was taken.

    Args:
        when: The moments to place, each read as UTC.

    Returns:
        The angle Mars had swept by each, in degrees, one to each moment given.
        The angles run on past 360 rather than turning over, so the arc between
        any two of them is what one subtracted from the other leaves.
    """
    return [
        _swept(moment.timestamp() / _DAY_SECONDS + _JD_UNIX_EPOCH - _J2000)
        for moment in when
    ]


def _swept(offset: float) -> float:
    """Work out the angle Mars has swept since J2000, without turning it over.

    The series follows Allison and McEwen (1997), the one the Mars24 algorithm is
    written from, less its seven small perturbers and the offset terrestrial time
    carries. Together those move the angle by under a thirtieth of a degree,
    which neither the width a window is held to nor the price it pays can feel.

    Args:
        offset: The days the moment stands after the J2000 epoch.

    Returns:
        The angle swept, in degrees, counted from a zero of no meaning. It only
        ever climbs: the mean sun runs at 0.524 degrees a day and the correction
        below moves at most 0.11, so the difference of any two is a true arc.
    """
    anomaly = math.radians(19.3871 + 0.52402073 * offset)
    # Where the true sun stands against the mean one, on Mars' eccentric orbit
    centre = (
        10.691 * math.sin(anomaly)
        + 0.623 * math.sin(2.0 * anomaly)
        + 0.050 * math.sin(3.0 * anomaly)
        + 0.005 * math.sin(4.0 * anomaly)
    )
    return 270.3871 + 0.524038496 * offset + centre

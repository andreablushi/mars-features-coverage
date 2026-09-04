"""Where Mars stood in its own year on a given date, and the season that makes it.

The solar longitude follows Allison and McEwen (1997), the series the Mars24
algorithm is written from, which holds to a hundredth of a degree.
"""

from __future__ import annotations

import math
from datetime import datetime

# The Julian date the Unix epoch falls on, which every timestamp is counted from
_JD_UNIX_EPOCH = 2440587.5

# Seconds in a day, which the Julian dates below are counted in
_DAY_SECONDS = 86400.0

# Terrestrial time runs ahead of UTC by the leap seconds and a fixed offset. The
# leap seconds have stood at 37 since 2017, and the few earlier ones move Ls by
# less than a ten-thousandth of a degree, so one offset answers for the record.
_TT_MINUS_UTC = 69.184

# The Julian date of the J2000 epoch the series below is written against
_J2000 = 2451545.0

# What perturbs Mars' orbit, as an amplitude in degrees, a period in days and a phase
_PERTURBERS = (
    (0.0071, 2.2353, 49.409),
    (0.0057, 2.7543, 168.173),
    (0.0039, 1.1177, 191.837),
    (0.0037, 15.7866, 21.736),
    (0.0021, 2.1354, 15.704),
    (0.0020, 2.4694, 95.528),
    (0.0018, 32.8493, 49.095),
)

# The Julian date Mars year 1 opened on, 11 April 1955, and how long a year runs
_JD_YEAR_ONE = 2435208.9583
_YEAR_DAYS = 686.9725

# How many seasons a Mars year is cut into, one to each quadrant of longitude
SEASONS_PER_YEAR = 4

# Each quadrant of solar longitude, named the way the northern hemisphere lives it
SEASON_NAMES = ("N spring", "N summer", "N autumn", "N winter")


def placed(when: datetime) -> tuple[float, int]:
    """Say where Mars stood in its year when an observation was taken.

    Args:
        when: The moment to place, which is read as UTC.

    Returns:
        The solar longitude in degrees, and the season it falls in as one number
        counting seasons from the opening of Mars year 1.
    """
    julian = (
        when.timestamp() / _DAY_SECONDS + _JD_UNIX_EPOCH + _TT_MINUS_UTC / _DAY_SECONDS
    )
    longitude = _areocentric(julian - _J2000)
    quadrant = int(longitude // (360.0 / SEASONS_PER_YEAR))
    return longitude, _year(julian, longitude) * SEASONS_PER_YEAR + quadrant


def named(season: int) -> tuple[int, str]:
    """Read a season back as the year and the name it is spoken of by.

    Args:
        season: The season counted from the opening of Mars year 1.

    Returns:
        The Mars year it falls in, and the name of the season inside that year.
    """
    year, quadrant = divmod(season, SEASONS_PER_YEAR)
    return year, SEASON_NAMES[quadrant]


def _areocentric(offset: float) -> float:
    """Work out the solar longitude at one moment of terrestrial time.

    Args:
        offset: The days that moment stands after the J2000 epoch.

    Returns:
        The solar longitude in degrees, from 0 at the northern spring equinox.
    """
    anomaly = math.radians(19.3871 + 0.52402073 * offset)
    mean_sun = 270.3871 + 0.524038496 * offset
    perturbation = sum(
        amplitude * math.cos(math.radians(0.985626 * offset / period + phase))
        for amplitude, period, phase in _PERTURBERS
    )
    # Where the true sun stands against the mean one, on Mars' eccentric orbit
    centre = (
        (10.691 + 3.0e-7 * offset) * math.sin(anomaly)
        + 0.623 * math.sin(2.0 * anomaly)
        + 0.050 * math.sin(3.0 * anomaly)
        + 0.005 * math.sin(4.0 * anomaly)
        + 0.0005 * math.sin(5.0 * anomaly)
        + perturbation
    )
    return (mean_sun + centre) % 360.0


def _year(julian: float, longitude: float) -> int:
    """Count which Mars year one moment falls in.

    Args:
        julian: The Julian date of that moment, in terrestrial time.
        longitude: The solar longitude it stands at, in degrees.

    Returns:
        The Mars year, counting the year opening in April 1955 as the first.
    """
    turns = (julian - _JD_YEAR_ONE) / _YEAR_DAYS
    year = math.floor(turns)
    # A mean year drifts off the real one, so the longitude settles the boundary
    drift = turns - year - longitude / 360.0
    if drift > 0.5:
        year += 1
    elif drift < -0.5:
        year -= 1
    return year + 1

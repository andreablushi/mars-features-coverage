"""How a measurement reads once it is put into words."""

from __future__ import annotations

from collections.abc import Callable

from sampling.models.spread import Spread
from utils.maths import quantities

NOTHING = "none"
UNCOUNTED = "not counted"

# The instrument whose pixels are radargram columns rather than picture elements.
SOUNDER = "SHARAD"


def spread(measured: Spread, written: Callable[[float], str]) -> str:
    """Write a measurement read off many tiles, and how far they sit from it.

    Args:
        measured: The measurement, tile by tile.
        written: How one of its numbers is put into words and units.

    Returns:
        The average, and the deviation after it where the tiles disagree.
    """
    if not measured.counted:
        return NOTHING
    middle = written(measured.mean)
    if measured.agreed:
        return middle
    return f"{middle} ± {written(measured.deviation)}"


def share(measured: Spread) -> str:
    """Write a share read off many tiles.

    Args:
        measured: The share, tile by tile.

    Returns:
        The average, and how far the tiles sit from it where they disagree.
    """
    if not measured.counted:
        return NOTHING
    if measured.agreed:
        return f"{measured.mean:.0%}"
    return f"{measured.mean:.0%} ± {measured.deviation:.0%}"


def span(measured: Spread) -> str:
    """Write a length of time read off many tiles.

    Args:
        measured: The length in days, tile by tile.

    Returns:
        The average, and the shortest and longest where the tiles disagree.
    """
    if not measured.counted:
        return NOTHING
    middle = quantities.duration(measured.mean)
    if measured.agreed:
        return middle
    return (
        f"{middle}, {quantities.duration(measured.low)} to "
        f"{quantities.duration(measured.high)}"
    )


def ground(km2: float, of_km2: float) -> str:
    """Write an amount of ground and what share of something it is.

    Args:
        km2: The ground in square kilometres.
        of_km2: The ground it is read back as a share of.

    Returns:
        The ground, or that there is none.
    """
    if not km2:
        return NOTHING
    if not of_km2:
        return quantities.area(km2)
    return f"{quantities.area(km2)}, {km2 / of_km2:.0%}"


def pixels(counted: float | None) -> str:
    """Write a pixel count.

    Args:
        counted: The pixels, or None where none were counted.

    Returns:
        The count, or that it was never measured.
    """
    if counted is None:
        return UNCOUNTED
    return f"{quantities.compact(counted)} px"


def landed(measured: Spread) -> str:
    """Write a pixel count read off many tiles.

    Args:
        measured: The pixels, tile by tile.

    Returns:
        The average, and how far the tiles sit from it where they disagree.
    """
    if not measured.counted:
        return UNCOUNTED
    middle = quantities.compact(measured.mean)
    if measured.agreed:
        return f"{middle} px"
    return f"{middle} px ± {quantities.compact(measured.deviation)} px"


def columns(measured: Spread) -> str:
    """Write a count of radargram columns read off many tiles.

    Args:
        measured: The columns, tile by tile.

    Returns:
        The average, and how far the tiles sit from it where they disagree.
    """
    if not measured.counted:
        return UNCOUNTED
    middle = quantities.compact(measured.mean)
    if measured.agreed:
        return middle
    return f"{middle} ± {quantities.compact(measured.deviation)}"


def tile(row: int, column: int) -> str:
    """Name one tile by where it sits on the feature's grid.

    Args:
        row: Its row, counting north from the south edge.
        column: Its column, counting east from the west edge.

    Returns:
        The name, counting from one at the south west corner.
    """
    return f"row {row + 1}, column {column + 1}"

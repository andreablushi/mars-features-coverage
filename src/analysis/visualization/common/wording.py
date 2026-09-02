"""How a measurement reads once it is put into words."""

from __future__ import annotations

from collections.abc import Callable

from analysis.sampling.models.spread import Spread
from analysis.utils.maths import quantities

NOTHING = "none"
UNCOUNTED = "not counted"

# The instrument whose pixels are radargram traces rather than picture elements.
SOUNDER = "SHARAD"


def counted(number: float, noun: str) -> str:
    """Write how many of something there are, with the noun made plural to match.

    Args:
        number: How many there are.
        noun: What they are, spelled singular and cased as the caller wants it.

    Returns:
        The count and the noun, such as "2 instruments".

    """
    return f"{number:,.0f} {noun}" + ("" if number == 1 else "s")


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
    return spread(measured, lambda held: f"{held:.0%}")


def landed(measured: Spread) -> str:
    """Write a pixel count read off many tiles.

    Args:
        measured: The pixels, tile by tile.

    Returns:
        The average, and how far the tiles sit from it where they disagree.
    """
    if not measured.counted:
        return UNCOUNTED
    return spread(measured, lambda counted: f"{quantities.compact(counted)} px")


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

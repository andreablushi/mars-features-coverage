"""How a measured quantity is written short enough to read at a glance."""

from __future__ import annotations

_STEPS = ((1e9, "G"), (1e6, "M"), (1e3, "k"))


def compact(value: float) -> str:
    """Write a count short enough to read at a glance.

    Args:
        value: The count.

    Returns:
        The count itself when it is small, and otherwise as thousands,
        millions, or billions.
    """
    for limit, suffix in _STEPS:
        if value >= limit:
            return f"{value / limit:,.2f} {suffix}"
    return f"{value:,.0f}"


def area(km2: float) -> str:
    """Write a ground area short enough to read at a glance.

    Args:
        km2: The area in square kilometres.

    Returns:
        The area, kept to a hundredth where it is smaller than ten square
        kilometres and rounded whole above that.
    """
    return f"{km2:,.0f} km2" if km2 >= 10.0 else f"{km2:,.2f} km2"

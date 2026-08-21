"""The trade off curve the candidate windows trace, ground against days."""

from __future__ import annotations

from collections.abc import Sequence


def unit(values: Sequence[float]) -> list[float]:
    """Rescale one axis of the curve so it runs from nought to one.

    Putting both axes on the same scale is what lets days and ground be
    compared at all without an exchange rate being invented between them.

    Args:
        values: The axis, in its own units.

    Returns:
        The same axis rescaled, or all zeros when it never varies.
    """
    low, high = min(values), max(values)
    if high == low:
        return [0.0] * len(values)
    return [(value - low) / (high - low) for value in values]

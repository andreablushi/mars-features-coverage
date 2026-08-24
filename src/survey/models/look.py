"""The least an instrument set left inside a window, on one tile."""

from __future__ import annotations

from dataclasses import dataclass

from models.results import Event


@dataclass(frozen=True, slots=True)
class Look:
    """One observation as the tile it was judged on saw it.

    An observation is admitted or turned away tile by tile, so what it left on
    the tile a window was found over is what the window was measured on. The
    ground it covers over the whole feature says nothing about that: a strip
    crossing a terra can clip one tile and fill the next.

    Attributes:
        observation: The observation itself.
        ground_km2: How much ground it covers inside that tile.
        pixels: How many of the instrument's pixels it landed there, or None
            when none were counted for it.
    """

    observation: Event
    ground_km2: float
    pixels: float | None

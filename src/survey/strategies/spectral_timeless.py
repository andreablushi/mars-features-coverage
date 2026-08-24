"""Composition and shape inside the window, depth from whenever it was read."""

from __future__ import annotations

from survey.models.strategy import Strategy

# The strictest strategy, with SHARAD asked of the whole record. CTX and CRISM
# both read the surface, so they stay inside the window and have to agree in
# time; only the sounder is let out of it.
SPECTRAL_TIMELESS = Strategy(
    name="spectral-timeless",
    demands={"SHARAD": 0.0, "CTX": 0.25, "CRISM": 0.10},
    crossing_km=50.0,
    timeless=frozenset({"SHARAD"}),
)

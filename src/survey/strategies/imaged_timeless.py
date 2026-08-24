"""A sounder that flew over at all, and an imager that covered the ground."""

from __future__ import annotations

from survey.models.strategy import Strategy

# The configured strategy, with SHARAD asked of the whole record. A sounder
# reads the rock under the ground, which the seasons do not turn, so the window
# is left to CTX and no longer stretches to the next time SHARAD flew over.
IMAGED_TIMELESS = Strategy(
    name="imaged-timeless",
    demands={"SHARAD": 0.0, "CTX": 0.25},
    crossing_km=50.0,
    span_days=687.0,
    timeless=frozenset({"SHARAD"}),
)

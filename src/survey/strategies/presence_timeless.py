"""Every instrument on the ground, with the sounder free of the window."""

from __future__ import annotations

from survey.models.strategy import Strategy

# Presence, with SHARAD asked of the whole record instead of the window. The
# window then closes around the imagery alone, so it is as short as one image.
PRESENCE_TIMELESS = Strategy(
    name="presence-timeless",
    demands={"SHARAD": 0.0, "CTX": 0.0},
    crossing_km=25.0,
    span_days=687.0,
    timeless=frozenset({"SHARAD"}),
)

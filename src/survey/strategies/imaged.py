"""A sounder track, and an imager that covered a real part of the ground."""

from __future__ import annotations

from survey.models.strategy import Strategy

# CTX images a swath and has been pointed at the whole planet, so asking it
# for a quarter of the ground asks for what it can give. SHARAD draws a line
# a few kilometres wide, so it is asked for a length rather than a share: half
# a tile's width, which is a track running properly through the ground.
IMAGED = Strategy(name="imaged", demands={"SHARAD": 0.0, "CTX": 0.25}, crossing_km=50.0)

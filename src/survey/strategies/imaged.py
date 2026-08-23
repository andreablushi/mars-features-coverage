"""A sounder track, and an imager that covered a real part of the ground."""

from __future__ import annotations

from survey.models.strategy import Strategy

# CTX images a swath and has been pointed at the whole planet, so asking it
# for a quarter of the ground asks for what it can give. SHARAD draws a line
# a few kilometres wide, so it is asked to be there and to have crossed,
# which is what the admissible filter already measures it against.
IMAGED = Strategy(name="imaged", demands={"SHARAD": 0.0, "CTX": 0.25})

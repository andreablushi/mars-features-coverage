"""Every instrument in the window, however little of the ground it reached."""

from __future__ import annotations

from survey.models.strategy import Strategy

# The loosest of the strategies: a sounder track and an image of the feature,
# taken close enough together to be one look at it, and nothing more. It asks
# the imager for no share of the ground, so it keeps the thinnest window that
# holds both instruments at once. Its sounder track has to run a quarter of a
# tile's width, which is the least that reads as a crossing rather than a clip.
PRESENCE = Strategy(
    name="presence", demands={"SHARAD": 0.0, "CTX": 0.0}, crossing_km=25.0
)

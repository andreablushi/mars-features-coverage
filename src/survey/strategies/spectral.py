"""A sounder track, an imager, and the spectra to go with them."""

from __future__ import annotations

from survey.models.strategy import Strategy

# The strictest of the strategies: composition as well as shape and depth.
# CRISM's multispectral survey is asked for less ground than CTX, since it
# maps in narrower strips and was pointed at far less of the planet.
SPECTRAL = Strategy(
    name="spectral",
    demands={"SHARAD": 0.0, "CTX": 0.25, "CRISM": 0.10},
    crossing_km=50.0,
)

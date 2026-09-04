"""What one build was asked to do, once the config has been read."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """The settled choices for a build, read from one flat config file.

    Attributes:
        features: How many features to build, or None for every one the
            selection kept.
        observations_per_feature: How many observations to keep of each, or
            None for every one it kept.
        instruments: Which instruments to build, as ODE names them.
        seed: The number every draw is made with, so a smaller build is a
            reproducible subset of the full one.
        workers: How many jobs to run at once.
        ready: How many downloaded products may wait at once for the builds to
            reach them, which is what keeps the downloads from racing ahead.
    """

    features: int | None
    observations_per_feature: int | None
    instruments: tuple[str, ...]
    seed: int
    workers: int
    ready: int

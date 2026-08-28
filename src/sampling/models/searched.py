"""One feature of the dataset, as one strategy's search left it."""

from __future__ import annotations

from dataclasses import dataclass

from sampling.models.tiles import TileStats


@dataclass(frozen=True, slots=True)
class Searched:
    """What searching every tile of one feature under one strategy left.

    Attributes:
        strategy: The strategy it was searched under.
        feature_class: The class the catalogue files the feature under.
        iids: The instruments it holds, in the order they are drawn.
        measured: The tiles the search ran over, as it left them.
    """

    strategy: str
    feature_class: str
    iids: list[str]
    measured: list[TileStats]

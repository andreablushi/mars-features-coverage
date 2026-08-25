"""Reading the computed features off disk and searching each of them."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial

from prediction import sets
from prediction.models import tiles
from prediction.models.tiles import TileStats
from storage import summary
from survey import strategies, studying

Named = tuple[str, str]
Progress = Callable[[int, int], None]


@dataclass(frozen=True, slots=True)
class Searched:
    """One feature of the dataset, searched under one strategy.

    Attributes:
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.
        strategy: The strategy it was searched under.
        iids: The instruments it holds, in the order they are drawn.
        measured: The tiles the search ran over, as it left them.
    """

    feature_class: str
    name: str
    strategy: str
    iids: list[str]
    measured: list[TileStats]


def sweep(
    under: Sequence[str],
    wanted: Sequence[Named],
    workers: int = 8,
    progress: Progress | None = None,
) -> list[Searched]:
    """Search every tile of every named feature under every strategy named.

    Args:
        under: The strategies to search under, by name.
        wanted: The features to search, as class and name.
        workers: How many processes to search on at once.
        progress: Called with how many features are done and how many there are.

    Returns:
        One entry per feature and strategy, in the order the features came in.
    """
    found: list[Searched] = []
    searching = partial(_searched, under=tuple(under))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for done, searched in enumerate(pool.map(searching, wanted, chunksize=1), 1):
            found.extend(searched)
            if progress is not None:
                progress(done, len(wanted))
    return found


def _searched(named: Named, under: Sequence[str]) -> list[Searched]:
    """Search every tile of one feature under every strategy named.

    Args:
        named: The feature's class and name.
        under: The strategies to search under, by name.

    Returns:
        One entry per strategy, and nothing where the feature has no set on disk.
    """
    feature_class, name = named
    coverage = sets.plotted(summary.load_feature(feature_class, name))
    if not coverage:
        return []
    found: list[Searched] = []
    for chosen in under:
        study = studying.study(coverage, strategies.named(chosen))
        found.append(
            Searched(
                feature_class=feature_class,
                name=name,
                strategy=chosen,
                iids=tiles.instruments(study),
                measured=tiles.measured(study),
            )
        )
    return found

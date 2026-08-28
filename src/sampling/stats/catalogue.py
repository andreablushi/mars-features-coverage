"""Reading the measured dataset as one, before any strategy is asked of it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from coverage import summary as index
from coverage.results import Summary
from metadata.catalog import read_features
from sampling.models.catalogue import CatalogueStats, InstrumentStats, Reach
from sampling.models.spread import Spread


def read() -> CatalogueStats:
    """Read the catalogue index as one dataset.

    Returns:
        What it holds, and nothing at all when no feature was measured.
    """
    rows = index.catalogued_rows()
    catalogued = read_features()
    # One row per feature carries the grid, which every set of it shares
    features: dict[tuple[str, str], Summary] = {}
    grouped: dict[str, list[Summary]] = {}
    for row in rows:
        features.setdefault((row.feature_class, row.feature_name), row)
        grouped.setdefault(row.iid, []).append(row)
    counted = Counter(feature_class for feature_class, _ in features)
    grounds: dict[str, list[float]] = {}
    for (feature_class, _), row in features.items():
        grounds.setdefault(feature_class, []).append(row.feature_area_km2)
    return CatalogueStats(
        catalogued=len(catalogued),
        features=len(features),
        points=sum(1 for feature in catalogued if feature.is_point),
        classes=dict(counted.most_common()),
        class_km2={name: Spread.over(held) for name, held in grounds.items()},
        area_km2=sum(row.feature_area_km2 for row in features.values()),
        instruments=sorted(
            (_instrument(iid, taken) for iid, taken in grouped.items()),
            key=lambda instrument: -instrument.observations,
        ),
    )


def _instrument(iid: str, taken: Sequence[Summary]) -> InstrumentStats:
    """Read what one instrument holds of every feature it reached.

    Args:
        iid: The instrument the rows belong to.
        taken: Its rows, one per feature and instrument set it measured.

    Returns:
        What it holds.
    """
    return InstrumentStats(
        iid=iid,
        features=len({(row.feature_class, row.feature_name) for row in taken}),
        observations=sum(row.n_obs for row in taken),
        covered_km2=sum(row.covered_km2 for row in taken),
        first=min(row.t_first for row in taken),
        last=max(row.t_last for row in taken),
        reach=[_reach(row) for row in taken],
    )


def _reach(row: Summary) -> Reach:
    """Read what one instrument reached of one feature.

    Args:
        row: The instrument's row for that feature.

    Returns:
        The feature's size, the share of it reached, and the pixels one look landed.
    """
    return Reach(
        area_km2=row.feature_area_km2,
        covered_frac=row.covered_frac,
        pixels_per_observation=row.pixels / row.n_obs if row.n_obs else 0.0,
    )

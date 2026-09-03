"""Reading the measured dataset as one, before the filter is asked of it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from analysis.coverage.artifacts import indexing
from analysis.coverage.measuring import overlaps
from analysis.coverage.models.summary import Summary
from analysis.metadata.loaders.features import load_features
from analysis.sampling.models.catalogue import CatalogueStats, InstrumentStats
from analysis.sampling.models.spread import Spread


def read_catalogue() -> CatalogueStats:
    """Read the catalogue index as one dataset.

    Returns:
        What it holds, and nothing at all when no feature was measured.
    """
    catalogued = load_features()
    # What the features hold once, since their boxes overlap one another
    shared = overlaps.read()
    # One row per feature carries the grid, which every set of it shares
    by_feature: dict[tuple[str, str], Summary] = {}
    by_instrument: dict[str, list[Summary]] = {}
    for row in indexing.catalogued_rows():
        by_feature.setdefault((row.feature_class, row.feature_name), row)
        by_instrument.setdefault(row.iid, []).append(row)
    km2_by_class: dict[str, list[float]] = {}
    for (feature_class, _), row in by_feature.items():
        km2_by_class.setdefault(feature_class, []).append(row.feature_area_km2)
    return CatalogueStats(
        catalogued=len(catalogued),
        features=len(by_feature),
        points=sum(1 for feature in catalogued if feature.is_point),
        classes=dict(Counter(name for name, _ in by_feature).most_common()),
        class_km2={name: Spread.over(km2) for name, km2 in km2_by_class.items()},
        area_km2=sum(row.feature_area_km2 for row in by_feature.values()),
        union_km2=shared.ground_km2 if shared else 0.0,
        instruments=sorted(
            (
                _instrument(
                    iid, rows, shared.covered_km2.get(iid, 0.0) if shared else 0.0
                )
                for iid, rows in by_instrument.items()
            ),
            key=lambda instrument: -instrument.observations,
        ),
    )


def _instrument(iid: str, rows: Sequence[Summary], union_km2: float) -> InstrumentStats:
    """Read what one instrument holds of every feature it reached.

    Args:
        iid: The instrument the rows belong to.
        rows: Its rows, one per feature and instrument set it measured.
        union_km2: The ground it reached counting shared ground once in all.

    Returns:
        What it holds.
    """
    observed: Counter[tuple[str, str]] = Counter()
    for row in rows:
        observed[row.feature_class, row.feature_name] += row.n_obs
    return InstrumentStats(
        iid=iid,
        features=len(observed),
        observations=sum(observed.values()),
        per_feature=Spread.over(list(observed.values())),
        covered_km2=sum(row.covered_km2 for row in rows),
        union_km2=union_km2,
        first=min(row.t_first for row in rows),
        last=max(row.t_last for row in rows),
    )

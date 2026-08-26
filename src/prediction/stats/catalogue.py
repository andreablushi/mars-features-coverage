"""Reading the measured dataset as one, before any strategy is asked of it."""

from __future__ import annotations

from models.results import Summary
from prediction.models.catalogue import CatalogueStats, InstrumentStats
from storage import summary as index


def read() -> CatalogueStats:
    """Read the catalogue index as one dataset.

    Returns:
        What it holds, and nothing at all when no feature was measured.
    """
    rows = index.catalogued_rows()
    # One row per feature carries the grid, which every set of it shares
    features: dict[tuple[str, str], Summary] = {}
    grouped: dict[str, list[Summary]] = {}
    for row in rows:
        features.setdefault((row.feature_class, row.feature_name), row)
        grouped.setdefault(row.iid, []).append(row)
    return CatalogueStats(
        features=len(features),
        classes=len({feature_class for feature_class, _ in features}),
        area_km2=sum(row.feature_area_km2 for row in features.values()),
        cells=sum(row.mask_cells for row in features.values()),
        tiles=sum(row.tiles_across**2 for row in features.values()),
        instruments=sorted(
            (
                InstrumentStats(
                    iid=iid,
                    features=len(
                        {(row.feature_class, row.feature_name) for row in taken}
                    ),
                    observations=sum(row.n_obs for row in taken),
                    pixels=sum(row.pixels for row in taken),
                    covered_km2=sum(row.covered_km2 for row in taken),
                    first=min(row.t_first for row in taken),
                    last=max(row.t_last for row in taken),
                )
                for iid, taken in grouped.items()
            ),
            key=lambda instrument: -instrument.observations,
        ),
    )

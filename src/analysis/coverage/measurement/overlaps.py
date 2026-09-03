"""The ground the features share, counted once however many of them hold it."""

from __future__ import annotations

import json
import math
from dataclasses import asdict

import numpy as np
import pyarrow.parquet as pq

import utils.disk.paths as paths
from analysis.coverage import configs
from analysis.coverage.artifacts import index
from analysis.coverage.models.grid import PlanetGrid
from analysis.coverage.models.overlap import Overlap
from analysis.coverage.models.summary import Summary
from analysis.coverage.projection.geometry import footprints, geodesy
from analysis.metadata.loaders.features import load_features
from analysis.models.feature import Feature
from analysis.utils.mask import cells_of
from utils.disk.files import atomic_path

OVERLAPS_NAME = "overlaps.json"


def overlaps() -> Overlap | None:
    """Return what the measured features hold between them, measuring it once.

    The measurement costs a pass over every observation the coverage stage
    left, so it is kept beside the index it was read from and made again only
    once that index has changed.

    Returns:
        The measurement, or None when no run has left an index to make one from.
    """
    summary_path = paths.catalog_summary_path()
    if not summary_path.is_file():
        return None
    stamp = f"{summary_path.stat().st_size}:{int(summary_path.stat().st_mtime)}"
    kept_path = paths.ARTIFACTS_ROOT / OVERLAPS_NAME
    if kept_path.is_file():
        kept = json.loads(kept_path.read_text(encoding="utf-8"))
        if kept.pop("stamp", None) == stamp:
            return Overlap(**kept)
    found = measure()
    with atomic_path(kept_path) as tmp:
        tmp.write_text(
            json.dumps({"stamp": stamp} | asdict(found), indent=1) + "\n",
            encoding="utf-8",
        )
    return found


def measure() -> Overlap:
    """Lay every measured feature onto one grid of Mars and count its cells once.

    Returns:
        What the features hold between them and what each instrument reached.
    """
    radius_km = configs.MARS_RADIUS_M / 1000.0
    grid = PlanetGrid(
        radius_km=radius_km,
        across=round(2.0 * math.pi * radius_km / configs.OVERLAP_CELL_KM),
        down=round(2.0 * radius_km / configs.OVERLAP_CELL_KM),
    )
    rows: dict[tuple[str, str], list[Summary]] = {}
    for row in index.catalogued_rows():
        rows.setdefault((row.feature_class, row.feature_name), []).append(row)
    named = {(one.feature_class, one.name): one for one in load_features()}
    ground = np.zeros(grid.cells, dtype=bool)
    reached = {
        row.iid: np.zeros(grid.cells, dtype=bool)
        for held in rows.values()
        for row in held
    }
    for key, held in rows.items():
        placed = _placed(grid, named[key], held[0])
        if placed is None:
            continue
        cells, local = placed
        # A dense lookup, since the cells are asked for far more often than set
        side = held[0].grid_side
        inside = _filled(cells_of(held[0].grid_mask), side)[local]
        if not inside.any():
            continue
        ground[cells[inside]] = True
        for iid, covered in _covered(key).items():
            reached[iid][cells[inside & _filled(covered, side)[local]]] = True
    return Overlap(
        cell_km2=grid.cell_km2,
        ground_km2=float(ground.sum()) * grid.cell_km2,
        covered_km2={
            iid: float(filled.sum()) * grid.cell_km2 for iid, filled in reached.items()
        },
    )


def _placed(
    grid: PlanetGrid, feature: Feature, row: Summary
) -> tuple[np.ndarray, np.ndarray] | None:
    """Say which of the planet's cells fall in one feature, and where in it.

    Args:
        grid: The grid of the planet the feature is laid on.
        feature: The feature, whose box bounds the cells to try.
        row: Any of its summary rows, which carries the grid it was measured on.

    Returns:
        The planet's cells whose centre falls inside the feature's own grid, and
        the cell of that grid each of them lands in, or None when none does.
    """
    # The columns wrap where the feature's box crosses the prime meridian
    west, east = feature.west_lon % 360.0, feature.east_lon % 360.0
    first = int(west / 360.0 * grid.across)
    last = min(grid.across, int(math.ceil(east / 360.0 * grid.across)) + 1)
    columns = (
        np.arange(first, last)
        if east >= west
        else np.r_[np.arange(first, grid.across), np.arange(0, last)]
    )
    low = int((math.sin(math.radians(feature.min_lat)) + 1.0) / 2.0 * grid.down)
    high = int(
        math.ceil((math.sin(math.radians(feature.max_lat)) + 1.0) / 2.0 * grid.down)
    )
    rows = np.arange(max(0, low), min(grid.down, high + 1))
    if not columns.size or not rows.size:
        return None
    across, down = (axis.ravel() for axis in np.meshgrid(columns, rows))
    lon = (across + 0.5) / grid.across * 360.0
    sine = np.clip((down + 0.5) / grid.down * 2.0 - 1.0, -1.0, 1.0)
    lat = np.degrees(np.arcsin(sine))

    region = footprints.feature_region(feature)
    west_m, south_m, east_m, north_m = region.shape.bounds
    x, y = geodesy.laea_forward(lon, lat, region.centre_lon, region.centre_lat)
    side = row.grid_side
    column = np.floor((x - west_m) / (east_m - west_m) * side).astype(np.int64)
    line = np.floor((y - south_m) / (north_m - south_m) * side).astype(np.int64)
    held = (column >= 0) & (column < side) & (line >= 0) & (line < side)
    if not held.any():
        return None
    return down[held] * grid.across + across[held], line[held] * side + column[held]


def _filled(cells: np.ndarray, side: int) -> np.ndarray:
    """Spread a list of cells out so any of them can be asked for at once.

    Args:
        cells: The cells filled, as their places on the feature's own grid.
        side: How many cells that grid holds along each axis.

    Returns:
        Whether each cell of the grid is one of them.
    """
    held = np.zeros(side * side, dtype=bool)
    held[cells] = True
    return held


def _covered(key: tuple[str, str]) -> dict[str, np.ndarray]:
    """Union the cells every observation of each instrument filled on one feature.

    Args:
        key: The feature's class and name.

    Returns:
        The cells of the feature's own grid each instrument reached, by instrument.
    """
    directory = paths.feature_artifacts_dir(paths.COVERAGE_ROOT, *key)
    found: dict[str, list[np.ndarray]] = {}
    for path in sorted(directory.glob(f"*{paths.EVENTS_SUFFIX}")):
        table = pq.read_table(path, columns=["iid", "mask"])
        for iid, mask in zip(
            table.column("iid").to_pylist(), table.column("mask").to_pylist()
        ):
            found.setdefault(iid, []).append(cells_of(mask))
    return {iid: np.unique(np.concatenate(parts)) for iid, parts in found.items()}

"""The ground the features share, counted once however many of them hold it.

A feature is a bounding box, and the boxes overlap: a crater sits inside a
terra sits inside a vastitas. Adding their grounds up therefore counts the same
ground several times, and adding up what an instrument reached of each of them
counts its work there several times too. Both are settled here by laying every
feature onto one grid of Mars and counting each of its cells once.

The measurement costs a pass over every observation the coverage stage left, so
it is worked out once and kept beside the index it was read from.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

import utils.disk.paths as paths
from analysis.coverage import configs
from analysis.coverage import summary as index
from analysis.coverage.geometry.region import FeatureRegion
from analysis.coverage.results import Summary
from analysis.coverage.utils import geodesy
from analysis.models.feature import Feature
from metadata.catalog import read_features
from utils.disk.files import atomic_path
from utils.maths.mask import cells_of

OVERLAPS_NAME = "overlaps.json"


@dataclass(frozen=True, slots=True)
class Overlap:
    """The ground the measured features hold between them, shared ground once.

    Attributes:
        cell_km2: How much ground one cell of the grid of Mars covers.
        ground_km2: The ground the features hold, counting shared ground once.
        covered_km2: The ground each instrument reached of it, by instrument,
            counting ground it reached on two overlapping features once.
    """

    cell_km2: float
    ground_km2: float
    covered_km2: dict[str, float]


def read(root: Path = paths.ARTIFACTS_ROOT) -> Overlap | None:
    """Read what the features share, measuring it when nothing was kept.

    Args:
        root: The artifacts root, holding the index and the kept measurement.

    Returns:
        The measurement, or None when there is no index to make one from.
    """
    index = paths.catalog_summary_path(root)
    if not index.is_file():
        return None
    path = root / OVERLAPS_NAME
    stamp = f"{index.stat().st_size}:{int(index.stat().st_mtime)}"
    if path.is_file():
        kept = json.loads(path.read_text(encoding="utf-8"))
        if kept.get("stamp") == stamp:
            return Overlap(
                cell_km2=kept["cell_km2"],
                ground_km2=kept["ground_km2"],
                covered_km2=kept["covered_km2"],
            )
    found = measure(root)
    written = {"stamp": stamp} | {
        "cell_km2": found.cell_km2,
        "ground_km2": found.ground_km2,
        "covered_km2": found.covered_km2,
    }
    with atomic_path(path) as tmp:
        tmp.write_text(json.dumps(written, indent=1) + "\n", encoding="utf-8")
    return found


def measure(root: Path = paths.ARTIFACTS_ROOT) -> Overlap:
    """Lay every measured feature onto one grid of Mars and count its cells once.

    Args:
        root: The artifacts root, holding the index and the per-feature files.

    Returns:
        What the features hold between them and what each instrument reached.
    """
    grid = _Grid(configs.OVERLAP_CELL_KM)
    rows: dict[tuple[str, str], list[Summary]] = {}
    for row in index.catalogued_rows(root):
        rows.setdefault((row.feature_class, row.feature_name), []).append(row)
    named = {(one.feature_class, one.name): one for one in read_features()}
    iids = sorted({row.iid for held in rows.values() for row in held})
    ground = np.zeros(grid.cells, dtype=bool)
    reached = {iid: np.zeros(grid.cells, dtype=bool) for iid in iids}
    for key, held in rows.items():
        feature = named.get(key)
        if feature is None:
            continue
        placed = grid.place(feature, held[0])
        if placed is None:
            continue
        cells, local = placed
        # A dense lookup, since the cells are asked for far more often than set
        side = held[0].grid_side
        inside = _filled(cells_of(held[0].grid_mask), side)[local]
        if not inside.any():
            continue
        ground[cells[inside]] = True
        for iid, covered in _covered(root, key).items():
            if iid in reached:
                hit = inside & _filled(covered, side)[local]
                reached[iid][cells[hit]] = True
    return Overlap(
        cell_km2=grid.cell_km2,
        ground_km2=float(ground.sum()) * grid.cell_km2,
        covered_km2={
            iid: float(filled.sum()) * grid.cell_km2 for iid, filled in reached.items()
        },
    )


class _Grid:
    """One equal-area grid of the whole of Mars, which every feature is laid on.

    Attributes:
        across: How many cells the grid holds around the equator.
        down: How many it holds from pole to pole.
        cells: How many it holds in all.
        cell_km2: How much ground one of them covers.
    """

    def __init__(self, cell_km: float) -> None:
        """Lay a grid of roughly square cells over the planet.

        The grid is cylindrical and equal area, so a cell covers the same ground
        wherever it falls, which is what lets the cells simply be counted.

        Args:
            cell_km: How wide a cell is at the equator, in kilometres.

        Returns:
            None.
        """
        radius_km = configs.MARS_RADIUS_M / 1000.0
        self.across = round(2.0 * math.pi * radius_km / cell_km)
        self.down = round(2.0 * radius_km / cell_km)
        self.cells = self.across * self.down
        self.cell_km2 = 4.0 * math.pi * radius_km**2 / self.cells

    def place(
        self, feature: Feature, row: Summary
    ) -> tuple[np.ndarray, np.ndarray] | None:
        """Say which of the planet's cells fall in one feature, and where in it.

        Args:
            feature: The feature, whose box bounds the cells to try.
            row: Any of its summary rows, which carries the grid it was measured on.

        Returns:
            The planet's cells whose centre falls inside the feature's own grid,
            and the cell of that grid each of them lands in, or None for none.
        """
        region = FeatureRegion(feature)
        west, south, east, north = region.shape.bounds
        if east <= west or north <= south:
            return None
        columns, rows = self._box(feature)
        if not columns.size or not rows.size:
            return None
        across, down = np.meshgrid(columns, rows)
        across, down = across.ravel(), down.ravel()
        lon, lat = self._centres(across, down)
        x, y = geodesy.laea_forward(lon, lat, region.centre_lon, region.centre_lat)
        side = row.grid_side
        column = np.floor((x - west) / (east - west) * side).astype(np.int64)
        line = np.floor((y - south) / (north - south) * side).astype(np.int64)
        held = (column >= 0) & (column < side) & (line >= 0) & (line < side)
        if not held.any():
            return None
        return down[held] * self.across + across[held], line[held] * side + column[held]

    def _box(self, feature: Feature) -> tuple[np.ndarray, np.ndarray]:
        """Return the grid's columns and rows the feature's box reaches.

        Args:
            feature: The feature whose box bounds them.

        Returns:
            The columns, wrapped where the box crosses the prime meridian, and
            the rows.
        """
        west, east = feature.west_lon % 360.0, feature.east_lon % 360.0
        first = int(west / 360.0 * self.across)
        last = min(self.across, int(math.ceil(east / 360.0 * self.across)) + 1)
        if east >= west:
            columns = np.arange(first, last)
        else:
            columns = np.r_[np.arange(first, self.across), np.arange(0, last)]
        low = int((math.sin(math.radians(feature.min_lat)) + 1.0) / 2.0 * self.down)
        high = int(
            math.ceil((math.sin(math.radians(feature.max_lat)) + 1.0) / 2.0 * self.down)
        )
        return columns, np.arange(max(0, low), min(self.down, high + 1))

    def _centres(
        self, across: np.ndarray, down: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return where the centre of each named cell falls on the planet.

        Args:
            across: The column of each cell.
            down: The row of each cell.

        Returns:
            The longitudes and latitudes of their centres, in degrees.
        """
        lon = (across + 0.5) / self.across * 360.0
        sine = np.clip((down + 0.5) / self.down * 2.0 - 1.0, -1.0, 1.0)
        return lon, np.degrees(np.arcsin(sine))


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


def _covered(root: Path, key: tuple[str, str]) -> dict[str, np.ndarray]:
    """Union the cells every observation of each instrument filled on one feature.

    Args:
        root: The artifacts root the per-feature files sit under.
        key: The feature's class and name.

    Returns:
        The cells of the feature's own grid each instrument reached, by instrument.
    """
    directory = paths.feature_artifacts_dir(root / "coverage", *key)
    found: dict[str, list[np.ndarray]] = {}
    for path in sorted(directory.glob(f"*{paths.EVENTS_SUFFIX}")):
        table = pq.read_table(path, columns=["iid", "mask"])
        for iid, mask in zip(
            table.column("iid").to_pylist(), table.column("mask").to_pylist()
        ):
            found.setdefault(iid, []).append(cells_of(mask))
    return {iid: np.unique(np.concatenate(parts)) for iid, parts in found.items()}

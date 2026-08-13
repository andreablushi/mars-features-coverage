"""Accumulating spatial coverage through time for one feature.

Observations are walked once, in chronological order across every instrument
set at once. Each is drawn a single time and folded into two running masks: the
one for its own instrument set, and the one pooling every instrument.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from analysis import configs, footprints, geodesy, swath
from analysis.grid import FeatureGrid
from analysis.models.feature import FeatureBox
from analysis.models.observation import Observation


def compute(
    box: FeatureBox, observations: Sequence[Observation]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Measure how each instrument set covers one feature over time.

    Args:
        box: The feature bounding box coverage is measured against.
        observations: The feature's observations in chronological order.

    Returns:
        One event row per observation and one summary row per instrument set,
        with a pooled row across every set appended to the summaries.
    """
    grid = FeatureGrid(box.min_lat, box.max_lat, box.west_lon, box.east_lon)
    widths = _track_widths(observations)
    area_km2 = grid.area_m2 / 1e6
    per_cell = area_km2 / grid.total_cells
    pooled = grid.empty_mask()
    pooled_cells = 0
    seen: dict[tuple[str, str, str], np.ndarray] = {}
    tallies: dict[tuple[str, str, str], int] = {}
    events: list[dict[str, Any]] = []

    for observation in observations:
        key = observation.set_key
        width_m, source = widths.get(observation.pdsid, (0.0, None))
        patch = grid.rasterize(footprints.parse(observation.wkt), width_m)
        covered = seen.setdefault(key, grid.empty_mask())
        fresh = patch.merge(covered)
        tallies[key] = tallies.get(key, 0) + fresh
        gridded = key in configs.GRIDDED_SETS
        pooled_fresh = 0 if gridded else patch.merge(pooled)
        pooled_cells += pooled_fresh
        events.append(
            _event(
                box,
                observation,
                own_cells=patch.cells,
                fresh_cells=fresh,
                set_cells=tallies[key],
                pooled_fresh_cells=pooled_fresh,
                pooled_cells=pooled_cells,
                total_cells=grid.total_cells,
                per_cell=per_cell,
                width_m=width_m,
                width_source=source,
                gridded=gridded,
            )
        )

    summaries = _summaries(box, observations, events, grid, pooled_cells, area_km2)
    return events, summaries


def _track_widths(
    observations: Sequence[Observation],
) -> dict[str, tuple[float, str]]:
    """Derive a swath width for every ground track in the feature.

    Args:
        observations: The feature's observations.

    Returns:
        The width in metres and its source, keyed by product identifier, for
        the track footprints only.
    """
    tracks = [observation for observation in observations if observation.is_track]
    if not tracks:
        return {}
    measurements = [
        (_track_length(observation.wkt), observation.duration_s)
        for observation in tracks
    ]
    resolved = swath.resolve_widths(measurements)
    return {
        observation.pdsid: width
        for observation, width in zip(tracks, resolved, strict=True)
    }


def _track_length(wkt: str) -> float:
    """Return the full ground length of a track footprint.

    The whole track is measured, not the part inside the feature, because the
    length is only used with the observation's duration to recover the ground
    speed the spacecraft flew at.

    Args:
        wkt: The footprint as well-known text.

    Returns:
        The summed length in metres.
    """
    total = 0.0
    for part in footprints.flatten(footprints.parse(wkt)):
        if part.geom_type != "LineString":
            continue
        coords = np.asarray(part.coords)
        total += geodesy.haversine_length(coords[:, 0], coords[:, 1])
    return total


def _event(
    box: FeatureBox,
    observation: Observation,
    *,
    own_cells: int,
    fresh_cells: int,
    set_cells: int,
    pooled_fresh_cells: int,
    pooled_cells: int,
    total_cells: int,
    per_cell: float,
    width_m: float,
    width_source: str | None,
    gridded: bool,
) -> dict[str, Any]:
    """Build the row recording what one observation contributed.

    Args:
        box: The feature being covered.
        observation: The observation being recorded.
        own_cells: Cells this footprint covers inside the feature.
        fresh_cells: Cells its instrument set had not covered before.
        set_cells: Cells its instrument set has covered up to and including it.
        pooled_fresh_cells: Cells no instrument had covered before.
        pooled_cells: Cells every instrument together has covered so far.
        total_cells: Cells making up the whole feature.
        per_cell: The area one cell stands for in square kilometres.
        width_m: The swath width used, zero when the footprint had area.
        width_source: Where the swath width came from, or None.
        gridded: Whether the observation is a whole-planet basemap.

    Returns:
        The event row.
    """
    return {
        "feature_class": box.feature_class,
        "feature_name": box.name,
        "ihid": observation.ihid,
        "iid": observation.iid,
        "pt": observation.pt,
        "pdsid": observation.pdsid,
        "t_start": observation.start,
        "t_stop": observation.stop,
        "own_km2": own_cells * per_cell,
        "new_km2": fresh_cells * per_cell,
        "cum_km2": set_cells * per_cell,
        "cum_frac": set_cells / total_cells,
        "new_all_km2": pooled_fresh_cells * per_cell,
        "cum_all_frac": pooled_cells / total_cells,
        "contributed": fresh_cells > 0,
        "width_km": width_m / 1000.0 if width_source else None,
        "width_source": width_source,
        "gridded": gridded,
    }


def _summaries(
    box: FeatureBox,
    observations: Sequence[Observation],
    events: Sequence[dict[str, Any]],
    grid: FeatureGrid,
    pooled_cells: int,
    area_km2: float,
) -> list[dict[str, Any]]:
    """Roll the events up into one row per instrument set, plus the pool.

    The pooled row leaves out whole-planet basemaps. Including them would put
    it at full coverage from its first event onwards and say nothing about what
    the targeted instruments actually reached.

    Args:
        box: The feature being covered.
        observations: The feature's observations.
        events: The event rows produced for them.
        grid: The raster the feature was measured on.
        pooled_cells: Cells covered by every non-basemap set together.
        area_km2: The feature's exact area in square kilometres.

    Returns:
        One summary row per instrument set followed by the pooled row.
    """
    rows: list[dict[str, Any]] = []
    keys = sorted({observation.set_key for observation in observations})
    for key in keys:
        member = [
            event
            for event in events
            if (event["ihid"], event["iid"], event["pt"]) == key
        ]
        rows.append(
            _summary(
                box,
                key,
                grid,
                area_km2,
                covered_frac=member[-1]["cum_frac"],
                count=len(member),
                contributing=sum(event["contributed"] for event in member),
                first=member[0]["t_start"],
                last=member[-1]["t_start"],
                gridded=key in configs.GRIDDED_SETS,
            )
        )
    label = configs.ALL_SETS_LABEL
    targeted = [event for event in events if not event["gridded"]]
    rows.append(
        _summary(
            box,
            (label, label, label),
            grid,
            area_km2,
            covered_frac=pooled_cells / grid.total_cells,
            count=len(targeted),
            contributing=sum(event["new_all_km2"] > 0.0 for event in targeted),
            first=targeted[0]["t_start"] if targeted else None,
            last=targeted[-1]["t_start"] if targeted else None,
            gridded=False,
        )
    )
    return rows


def _summary(
    box: FeatureBox,
    key: tuple[str, str, str],
    grid: FeatureGrid,
    area_km2: float,
    *,
    covered_frac: float,
    count: int,
    contributing: int,
    first: Any,
    last: Any,
    gridded: bool,
) -> dict[str, Any]:
    """Build one summary row.

    Args:
        box: The feature being covered.
        key: The instrument host, instrument, and product type.
        grid: The raster the feature was measured on.
        area_km2: The feature's exact area in square kilometres.
        covered_frac: The share of the feature ending up covered.
        count: How many observations the row covers.
        contributing: How many of them added area nothing had covered before.
        first: When the earliest of them started.
        last: When the latest of them started.
        gridded: Whether the row describes a whole-planet basemap.

    Returns:
        The summary row.
    """
    return {
        "feature_class": box.feature_class,
        "feature_name": box.name,
        "ihid": key[0],
        "iid": key[1],
        "pt": key[2],
        "feature_area_km2": area_km2,
        "covered_km2": covered_frac * area_km2,
        "covered_frac": covered_frac,
        "n_obs": count,
        "n_contributing": contributing,
        "t_first": first,
        "t_last": last,
        "span_days": (
            (last - first).total_seconds() / 86400.0 if first and last else None
        ),
        "cell_km": grid.cell_m / 1000.0,
        "gridded": gridded,
    }

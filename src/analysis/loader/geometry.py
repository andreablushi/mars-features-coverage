"""Caching projected footprints so a re-run does not redo the projection.

Parsing a footprint out of JSONL, densifying it, projecting it and cutting it
to its feature gives the same answer every time. Only the accumulation that
follows depends on anything else, so the projected result is written once as
well-known binary and read back on later runs.

The cache is keyed by the source file's modification time and by the version of
the projection rule that built it. A re-downloaded instrument set invalidates its
own cache and nothing else; a changed projection, segment step or swath model
invalidates every cache at once, by way of GEOMETRY_VERSION.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pyarrow.parquet as pq
from shapely import from_wkb, to_wkb

from analysis import configs
from analysis.loader import writer
from analysis.models.feature import FeatureBox
from analysis.models.projected import ProjectedObservation
from analysis.models.schemas import GEOMETRY, GEOMETRY_VERSION_KEY


def load(
    path: Path, source: Path
) -> tuple[FeatureBox, list[ProjectedObservation]] | None:
    """Read projected footprints back from the cache.

    Args:
        path: The geometry cache file.
        source: The metadata file the cache was built from.

    Returns:
        The feature box and its projected observations, or None when the cache
        is missing or older than the metadata it came from.
    """
    if not path.exists() or path.stat().st_mtime < source.stat().st_mtime:
        return None
    stored = pq.read_schema(path).metadata or {}
    if stored.get(GEOMETRY_VERSION_KEY) != configs.GEOMETRY_VERSION:
        return None
    rows = pq.read_table(path, schema=GEOMETRY).to_pylist()
    if not rows:
        return None
    first = rows[0]
    box = FeatureBox(
        name=first["feature_name"],
        feature_class=first["feature_class"],
        min_lat=first["min_lat"],
        max_lat=first["max_lat"],
        west_lon=first["west_lon"],
        east_lon=first["east_lon"],
    )
    return box, [
        ProjectedObservation(
            pdsid=row["pdsid"],
            ihid=row["ihid"],
            iid=row["iid"],
            pt=row["pt"],
            start=row["t_start"],
            stop=row["t_stop"],
            shape=from_wkb(row["wkb"]),
            width_km=row["width_km"],
            width_source=row["width_source"],
        )
        for row in rows
    ]


def save(
    path: Path, box: FeatureBox, observations: Sequence[ProjectedObservation]
) -> None:
    """Write projected footprints to the cache.

    Args:
        path: The geometry cache file.
        box: The feature the footprints were projected onto.
        observations: The projected observations to store.

    Returns:
        None.
    """
    rows = [
        {
            "feature_class": box.feature_class,
            "feature_name": box.name,
            "min_lat": box.min_lat,
            "max_lat": box.max_lat,
            "west_lon": box.west_lon,
            "east_lon": box.east_lon,
            "pdsid": observation.pdsid,
            "ihid": observation.ihid,
            "iid": observation.iid,
            "pt": observation.pt,
            "t_start": observation.start,
            "t_stop": observation.stop,
            "width_km": observation.width_km,
            "width_source": observation.width_source,
            "wkb": to_wkb(observation.shape),
        }
        for observation in observations
    ]
    writer.write_rows(rows, GEOMETRY, path)

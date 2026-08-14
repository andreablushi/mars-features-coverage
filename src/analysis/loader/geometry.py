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

import numpy as np
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
    table = pq.read_table(path, schema=GEOMETRY)
    if not table.num_rows:
        return None
    columns = {name: table.column(name).to_pylist() for name in GEOMETRY.names}
    box = FeatureBox(
        name=columns["feature_name"][0],
        feature_class=columns["feature_class"][0],
        min_lat=columns["min_lat"][0],
        max_lat=columns["max_lat"][0],
        west_lon=columns["west_lon"][0],
        east_lon=columns["east_lon"][0],
    )
    shapes = from_wkb(np.asarray(columns["wkb"], dtype=object))
    return box, [
        ProjectedObservation(
            pdsid=pdsid,
            ihid=ihid,
            iid=iid,
            pt=pt,
            start=start,
            stop=stop,
            shape=shape,
            width_km=width_km,
            width_source=width_source,
        )
        for pdsid, ihid, iid, pt, start, stop, shape, width_km, width_source in zip(
            columns["pdsid"],
            columns["ihid"],
            columns["iid"],
            columns["pt"],
            columns["t_start"],
            columns["t_stop"],
            shapes,
            columns["width_km"],
            columns["width_source"],
            strict=True,
        )
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
    count = len(observations)
    columns = {
        "feature_class": [box.feature_class] * count,
        "feature_name": [box.name] * count,
        "min_lat": [box.min_lat] * count,
        "max_lat": [box.max_lat] * count,
        "west_lon": [box.west_lon] * count,
        "east_lon": [box.east_lon] * count,
        "pdsid": [observation.pdsid for observation in observations],
        "ihid": [observation.ihid for observation in observations],
        "iid": [observation.iid for observation in observations],
        "pt": [observation.pt for observation in observations],
        "t_start": [observation.start for observation in observations],
        "t_stop": [observation.stop for observation in observations],
        "width_km": [observation.width_km for observation in observations],
        "width_source": [observation.width_source for observation in observations],
        "wkb": to_wkb(
            np.asarray(
                [observation.shape for observation in observations], dtype=object
            )
        ).tolist(),
    }
    writer.write_columns(columns, GEOMETRY, path)

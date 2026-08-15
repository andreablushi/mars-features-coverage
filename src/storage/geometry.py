"""Caching projected footprints so a re-run does not redo the projection."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from shapely import from_wkb, to_wkb

from analysis import configs
from models.feature import Feature
from models.observation import LoadedSet, ProjectedObservation
from storage import parquet
from storage.schemas import GEOMETRY, GEOMETRY_VERSION_KEY


def load(path: Path, source: Path) -> LoadedSet[ProjectedObservation] | None:
    """Read projected footprints back from the cache.

    Args:
        path: The geometry cache file.
        source: The metadata file the cache was built from.

    Returns:
        The set as cached, reporting no discards because only a set that
        yielded something is ever cached, or None when the cache is missing or
        older than the metadata it came from.
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
    box = Feature(
        name=columns["feature_name"][0],
        feature_class=columns["feature_class"][0],
        min_lat=columns["min_lat"][0],
        max_lat=columns["max_lat"][0],
        west_lon=columns["west_lon"][0],
        east_lon=columns["east_lon"][0],
    )
    shapes = from_wkb(np.asarray(columns["wkb"], dtype=object))
    observations = [
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
    return LoadedSet(
        feature=box, set_key=columns["set_key"][0], observations=observations
    )


def save(
    path: Path,
    box: Feature,
    set_key: str,
    observations: Sequence[ProjectedObservation],
) -> None:
    """Write projected footprints to the cache.

    Args:
        path: The geometry cache file.
        box: The feature the footprints were projected onto.
        set_key: The instrument set the footprints were downloaded for.
        observations: The projected observations to store.

    Returns:
        None.
    """
    count = len(observations)
    columns = {
        "feature_class": [box.feature_class] * count,
        "feature_name": [box.name] * count,
        "set_key": [set_key] * count,
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
    parquet.write_columns(columns, GEOMETRY, path)

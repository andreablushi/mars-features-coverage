"""Reading one instrument set's downloaded observation metadata off disk."""

from __future__ import annotations

from itertools import chain
from pathlib import Path

import analysis.utils.provenance as provenance
from analysis.coverage.models.observation import LoadedSet, Observation
from utils.disk.files import read_jsonl


def load_set(path: Path) -> LoadedSet[Observation]:
    """Read the observations stored for one feature and instrument set.

    Args:
        path: The JSONL file holding the set's observations.

    Returns:
        The set as stored.
    """
    stored = read_jsonl(path)
    first = next(stored)
    box, set_key = provenance.feature_of(first), provenance.set_key_of(first)
    observations: list[Observation] = []
    discarded = 0
    for item in chain([first], stored):
        # A record with no footprint or no start time cannot be placed at all
        wkt, start = item.get("Footprint_C0_geometry"), item.get("UTC_start_time")
        if not wkt or not start:
            discarded += 1
            continue
        stop, scale = item.get("UTC_stop_time"), item.get("Map_scale")
        observations.append(
            Observation(
                pdsid=item["pdsid"],
                ihid=item["ihid"],
                iid=item["iid"],
                pt=item["pt"],
                start=provenance.as_utc(start),
                stop=provenance.as_utc(stop) if stop else None,
                wkt=wkt,
                map_scale_m=float(scale) if scale else None,
            )
        )
    observations.sort(key=lambda observation: (observation.start, observation.pdsid))
    return LoadedSet(
        feature=box, set_key=set_key, observations=observations, discarded=discarded
    )

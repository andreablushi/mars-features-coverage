"""Reading one instrument set's downloaded observation metadata off disk."""

from __future__ import annotations

from itertools import chain
from pathlib import Path
from typing import Any

import utils.disk.provenance as provenance
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
        observation = _observation(item)
        if observation is None:
            discarded += 1
        else:
            observations.append(observation)
    observations.sort(key=lambda observation: (observation.start, observation.pdsid))
    return LoadedSet(
        feature=box, set_key=set_key, observations=observations, discarded=discarded
    )


def _observation(item: dict[str, Any]) -> Observation | None:
    """Build an observation from a stored record.

    Args:
        item: One stored observation record.

    Returns:
        The observation, or None when it carries no footprint or no start time.
    """
    wkt = item.get("Footprint_C0_geometry")
    start, stop = item.get("UTC_start_time"), item.get("UTC_stop_time")
    scale = item.get("Map_scale")
    if not wkt or not start:
        return None
    return Observation(
        pdsid=item["pdsid"],
        ihid=item["ihid"],
        iid=item["iid"],
        pt=item["pt"],
        start=provenance.as_utc(start),
        stop=provenance.as_utc(stop) if stop else None,
        wkt=wkt,
        map_scale_m=float(scale) if scale else None,
    )

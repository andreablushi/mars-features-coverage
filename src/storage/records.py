"""Reading one instrument set's downloaded observation metadata off disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import utils.provenance as provenance
from models.observation import LoadedSet, Observation
from storage.disk import read_jsonl


def load_set(path: Path) -> LoadedSet[Observation] | None:
    """Read the observations stored for one feature and instrument set.

    Args:
        path: The JSONL file holding the set's observations.

    Returns:
        The set as stored, or None when the file held no records at all.
    """
    box = None
    set_key = ""
    observations: list[Observation] = []
    discarded = 0
    for item in read_jsonl(path):
        if box is None:
            box, set_key = provenance.feature_of(item), provenance.set_key_of(item)
        observation = _observation(item)
        if observation is None:
            discarded += 1
        else:
            observations.append(observation)
    if box is None:
        return None
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
    )

"""Reading one instrument set's downloaded observation metadata off disk."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models.feature import Feature
from models.observation import LoadedSet, Observation
from storage.files import read_jsonl


def load_set(path: Path) -> LoadedSet[Observation] | None:
    """Read the observations stored for one feature and instrument set.

    Records that cannot be placed on the map or on the time axis are counted
    rather than dropped quietly, so a set that yields nothing is reported as
    such instead of passing for a set that had nothing to say.

    Args:
        path: The JSONL file holding the set's observations.

    Returns:
        The set as stored, or None when the file held no records at all.
    """
    box: Feature | None = None
    set_key = ""
    observations: list[Observation] = []
    discarded = 0
    for item in read_jsonl(path):
        if box is None:
            box, set_key = _box(item), _set_key(item)
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


def _set_key(item: dict[str, Any]) -> str:
    """Return the instrument set a record was downloaded for.

    Args:
        item: One stored observation record.

    Returns:
        The set identifier from provenance, falling back to the record's own
        product type for metadata written before provenance carried one.
    """
    stored = item.get("instrument_set")
    if stored:
        return str(stored)
    return f"{item['ihid']}/{item['iid']}/{item['pt']}"


def _box(item: dict[str, Any]) -> Feature:
    """Rebuild the feature box from a record's stored provenance.

    Args:
        item: One stored observation record.

    Returns:
        The feature box the record was downloaded for.
    """
    return Feature(
        name=item["feature_name"],
        feature_class=item["feature_class"],
        min_lat=float(item["feature_min_lat"]),
        max_lat=float(item["feature_max_lat"]),
        west_lon=float(item["feature_west_lon"]),
        east_lon=float(item["feature_east_lon"]),
    )


def _observation(item: dict[str, Any]) -> Observation | None:
    """Build an observation from a stored record.

    A footprint and a start time are what coverage needs: one to draw the
    ground, one to place it in time. The stop time is not required, because it
    only refines a track's swath width, which already falls back when it is
    missing, and it would otherwise cost the whole observation.

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
        start=_utc(start),
        stop=_utc(stop) if stop else None,
        wkt=wkt,
    )


def _utc(stamp: str) -> datetime:
    """Parse an ODE timestamp as UTC.

    ODE writes some product types with a trailing zone and others without, so
    a bare timestamp is read as the UTC it already is rather than as local time.

    Args:
        stamp: The ISO 8601 timestamp as stored.

    Returns:
        The timezone-aware timestamp.
    """
    parsed = datetime.fromisoformat(stamp)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

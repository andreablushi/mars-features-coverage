"""Reading one feature's downloaded observation metadata off disk."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.models.feature import FeatureBox
from analysis.models.observation import Observation
from analysis.models.records import FeatureData
from common.jsonl import read_jsonl


def load_feature(directory: Path) -> FeatureData | None:
    """Read every instrument set stored for one feature.

    Args:
        directory: The feature directory holding one JSONL file per set.

    Returns:
        The feature's box and its observations sorted into chronological order
        across every instrument set, or None when nothing usable was stored.
    """
    box: FeatureBox | None = None
    observations: list[Observation] = []
    for path in sorted(directory.glob("*.jsonl")):
        for item in read_jsonl(path):
            if box is None:
                box = _box(item)
            observation = _observation(item)
            if observation is not None:
                observations.append(observation)
    if box is None or not observations:
        return None
    observations.sort(key=lambda observation: (observation.start, observation.pdsid))
    return FeatureData(box=box, observations=observations)


def _box(item: dict[str, Any]) -> FeatureBox:
    """Rebuild the feature box from a record's stored provenance.

    Args:
        item: One stored observation record.

    Returns:
        The feature box the record was downloaded for.
    """
    return FeatureBox(
        name=item["feature_name"],
        feature_class=item["feature_class"],
        min_lat=float(item["feature_min_lat"]),
        max_lat=float(item["feature_max_lat"]),
        west_lon=float(item["feature_west_lon"]),
        east_lon=float(item["feature_east_lon"]),
    )


def _observation(item: dict[str, Any]) -> Observation | None:
    """Build an observation from a stored record.

    Args:
        item: One stored observation record.

    Returns:
        The observation, or None when it carries no footprint or no usable
        pair of timestamps.
    """
    wkt = item.get("Footprint_C0_geometry")
    start, stop = item.get("UTC_start_time"), item.get("UTC_stop_time")
    if not wkt or not start or not stop:
        return None
    return Observation(
        pdsid=item["pdsid"],
        ihid=item["ihid"],
        iid=item["iid"],
        pt=item["pt"],
        start=_utc(start),
        stop=_utc(stop),
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

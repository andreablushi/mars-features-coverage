"""Loading one feature's downloaded observation metadata off disk.

Footprints stay as text until the moment they are drawn. A large feature holds
far more observations than geometries that need to exist at once, so parsing
lazily keeps a worker's memory flat in the size of the raster rather than the
size of the feature.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class FeatureBox:
    """The bounding box coverage is measured against.

    Attributes:
        name: The feature name as ODE spells it.
        feature_class: The feature class, such as Crater or Collis.
        min_lat: The southernmost latitude in degrees.
        max_lat: The northernmost latitude in degrees.
        west_lon: The westernmost longitude in degrees.
        east_lon: The easternmost longitude in degrees.
    """

    name: str
    feature_class: str
    min_lat: float
    max_lat: float
    west_lon: float
    east_lon: float


@dataclass(frozen=True, slots=True)
class Observation:
    """One downloaded observation awaiting rasterization.

    Attributes:
        pdsid: The PDS product identifier.
        ihid: The instrument host identifier.
        iid: The instrument identifier.
        pt: The product type.
        start: When the observation started.
        stop: When the observation finished.
        wkt: The footprint as well-known text, left unparsed.
    """

    pdsid: str
    ihid: str
    iid: str
    pt: str
    start: datetime
    stop: datetime
    wkt: str

    @property
    def set_key(self) -> tuple[str, str, str]:
        """Return the instrument set this observation belongs to.

        Returns:
            The instrument host, instrument, and product type.
        """
        return (self.ihid, self.iid, self.pt)

    @property
    def is_track(self) -> bool:
        """Report whether the footprint is a ground track rather than an area.

        Returns:
            True when the footprint carries no polygon and must be buffered.
        """
        return self.wkt.startswith(("LINESTRING", "MULTILINESTRING"))

    @property
    def duration_s(self) -> float:
        """Return how long the observation lasted.

        Returns:
            The elapsed time in seconds.
        """
        return (self.stop - self.start).total_seconds()


def load_feature(directory: Path) -> tuple[FeatureBox | None, list[Observation]]:
    """Read every instrument set stored for one feature.

    Args:
        directory: The feature directory holding one JSONL file per set.

    Returns:
        The feature box taken from the stored provenance, or None when the
        directory holds nothing usable, and the observations sorted into
        chronological order across every instrument set.
    """
    box: FeatureBox | None = None
    observations: list[Observation] = []
    for path in sorted(directory.glob("*.jsonl")):
        with path.open() as handle:
            for line in handle:
                item = json.loads(line)
                if box is None:
                    box = _box(item)
                observation = _observation(item)
                if observation is not None:
                    observations.append(observation)
    observations.sort(key=lambda observation: (observation.start, observation.pdsid))
    return box, observations


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

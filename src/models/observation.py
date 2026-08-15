"""One downloaded observation, as coverage sees it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from shapely.geometry.base import BaseGeometry

from models.feature import Feature


@dataclass(frozen=True, slots=True)
class LoadedSet[T]:
    """One instrument set's observations, and what they belong to.

    The set is named by the key the run asked ODE for rather than by the
    product type its records carry, because a run can narrow one product type
    to a single observing mode and the records cannot tell which one was meant.

    Attributes:
        feature: The feature box the records were downloaded for.
        set_key: The instrument set identifier the records were asked for by.
        observations: The set's observations, in chronological order.
        discarded: How many records could not be used.
    """

    feature: Feature
    set_key: str
    observations: list[T]
    discarded: int = 0


@dataclass(frozen=True, slots=True)
class Observation:
    """One downloaded observation awaiting projection.

    The footprint stays as text until the moment it is drawn. A large feature
    holds far more observations than geometries that need to exist at once, so
    parsing lazily keeps only the geometries actually in use alive.

    Attributes:
        pdsid: The PDS product identifier.
        ihid: The instrument host identifier.
        iid: The instrument identifier.
        pt: The product type.
        start: When the observation started.
        stop: When the observation finished, or None when none was published.
        wkt: The footprint as well-known text, left unparsed.
    """

    pdsid: str
    ihid: str
    iid: str
    pt: str
    start: datetime
    stop: datetime | None
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
            The elapsed time in seconds, or zero when no stop was published,
            which leaves a track to take the fallback swath width.
        """
        return (self.stop - self.start).total_seconds() if self.stop else 0.0


@dataclass(frozen=True, slots=True)
class ProjectedObservation:
    """One observation's ground, ready to be folded into a union.

    Projecting a footprint costs the same on every run and depends only on the
    feature it is measured against, so the result is cached and this is what
    comes back.

    Attributes:
        pdsid: The PDS product identifier.
        ihid: The instrument host identifier.
        iid: The instrument identifier.
        pt: The product type.
        start: When the observation started.
        stop: When the observation finished, or None when none was published.
        shape: The projected footprint, clipped to the feature.
        width_km: The swath width used, or None when the footprint had area.
        width_source: Where the swath width came from, or None.
    """

    pdsid: str
    ihid: str
    iid: str
    pt: str
    start: datetime
    stop: datetime | None
    shape: BaseGeometry
    width_km: float | None
    width_source: str | None

    @property
    def set_key(self) -> tuple[str, str, str]:
        """Return the instrument set this observation belongs to.

        Returns:
            The instrument host, instrument, and product type.
        """
        return (self.ihid, self.iid, self.pt)

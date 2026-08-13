"""An observation once its footprint has been projected onto its feature."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from shapely.geometry.base import BaseGeometry


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

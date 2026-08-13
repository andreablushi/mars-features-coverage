"""One downloaded observation, as coverage sees it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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

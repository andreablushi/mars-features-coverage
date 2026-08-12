"""Data models for ODE geological features and instrument sets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    """A named geological feature with its bounding box.

    Attributes:
        name: The feature name (for example "Gale").
        feature_class: The feature class or type (for example "Crater").
        min_lat: Minimum planetocentric latitude in degrees.
        max_lat: Maximum planetocentric latitude in degrees.
        west_lon: Westernmost longitude in degrees, 0 to 360.
        east_lon: Easternmost longitude in degrees, 0 to 360.
    """

    name: str
    feature_class: str
    min_lat: float
    max_lat: float
    west_lon: float
    east_lon: float

    @property
    def is_degenerate(self) -> bool:
        """Return whether the bounding box has no positive latitude span.

        ODE rejects any query whose minimum latitude is not strictly less than
        its maximum latitude, so degenerate features must be skipped before
        querying.

        Returns:
            True when the latitude span is zero or negative.
        """
        return self.min_lat >= self.max_lat


@dataclass(frozen=True)
class InstrumentSet:
    """An ODE instrument host, instrument, and product type triple.

    Attributes:
        ihid: Instrument host id (for example "MRO").
        iid: Instrument id (for example "CTX").
        pt: Product type (for example "EDR").
    """

    ihid: str
    iid: str
    pt: str

    @property
    def key(self) -> str:
        """Return the canonical IHID/IID/PT identifier.

        Returns:
            The three identifiers joined by slashes.
        """
        return f"{self.ihid}/{self.iid}/{self.pt}"

    @property
    def slug(self) -> str:
        """Return a filesystem safe name for this instrument set.

        Returns:
            The three identifiers joined by underscores, with slashes and
            whitespace replaced by dashes.
        """
        raw = f"{self.ihid}_{self.iid}_{self.pt}"
        return raw.replace("/", "-").replace(" ", "-")

    @classmethod
    def parse(cls, text: str) -> InstrumentSet:
        """Build an instrument set from an "IHID/IID/PT" string.

        Args:
            text: A triple such as "MRO/CTX/EDR".

        Returns:
            The parsed instrument set.

        Raises:
            ValueError: If the text does not have exactly three parts.
        """
        parts = [part.strip() for part in text.split("/")]
        if len(parts) != 3 or not all(parts):
            raise ValueError(f"instrument must be IHID/IID/PT, got {text!r}")
        return cls(ihid=parts[0], iid=parts[1], pt=parts[2])

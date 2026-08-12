"""Instrument set model."""

from __future__ import annotations

from dataclasses import dataclass


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

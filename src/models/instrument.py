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

"""Instrument set model."""

from __future__ import annotations

from dataclasses import dataclass

from utils import slugify


@dataclass(frozen=True)
class InstrumentSet:
    """An ODE instrument host, instrument, and product type triple.

    Attributes:
        ihid: Instrument host id (for example "MRO").
        iid: Instrument id (for example "CTX").
        pt: Product type (for example "EDR").
        product_id: An ODE product id pattern the set is narrowed to.
    """

    ihid: str
    iid: str
    pt: str
    product_id: str | None = None

    @classmethod
    def from_key(cls, key: str) -> InstrumentSet:
        """Build a set from its canonical identifier.

        Args:
            key: An IHID/IID/PT triple, optionally followed by a colon and a
                product id pattern.

        Returns:
            The instrument set.
        """
        triple, _, pattern = key.partition(":")
        return cls(
            *(part.strip() for part in triple.split("/")),
            product_id=pattern.strip() or None,
        )

    @property
    def label(self) -> str:
        """Return the short readable name for this set.

        Returns:
            The instrument and product type, with the pattern appended when the
            set is only part of that type, such as "CRISM TRDR [mh]sp*".
        """
        name = f"{self.iid} {self.pt}"
        return f"{name} {self.product_id}" if self.product_id else name

    @property
    def key(self) -> str:
        """Return the canonical IHID/IID/PT identifier.

        Returns:
            The three identifiers joined by slashes, followed by the product id
            pattern after a colon when the set carries one.
        """
        key = f"{self.ihid}/{self.iid}/{self.pt}"
        return f"{key}:{self.product_id}" if self.product_id else key

    @property
    def slug(self) -> str:
        """Return a filesystem safe name for this instrument set.

        A pattern is spelled out in the name, so narrowing a set writes beside
        the whole one rather than silently overwriting it.

        Returns:
            The canonical identifier as a slug.
        """
        return slugify(self.key)


@dataclass(frozen=True)
class InstrumentSetInfo:
    """Catalog details for one instrument set as reported by ODE.

    Attributes:
        ihid: Instrument host id.
        iid: Instrument id.
        pt: Product type.
        instrument_name: Human readable instrument name.
        product_type_name: Human readable product type name.
        valid_footprints: Whether products carry usable footprints.
        valid_observation_times: Whether products carry observation times.
        number_products: Total products ODE holds, when reported.
    """

    ihid: str
    iid: str
    pt: str
    instrument_name: str | None
    product_type_name: str | None
    valid_footprints: bool
    valid_observation_times: bool
    number_products: int | None

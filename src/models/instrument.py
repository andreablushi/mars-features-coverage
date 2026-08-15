"""Instrument set model."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERN_PUNCTUATION = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True)
class InstrumentSet:
    """An ODE instrument host, instrument, and product type triple.

    A product type is sometimes one archive holding several observing modes at
    once, which a coverage measurement has no business adding together: CRISM
    files its 18 m targeted images, its 200 m survey strips and its off-nadir
    gimbal scans all under TRDR. The optional pattern narrows the set to the
    mode being measured, and ODE applies it, so the rest is never downloaded.

    Attributes:
        ihid: Instrument host id (for example "MRO").
        iid: Instrument id (for example "CTX").
        pt: Product type (for example "EDR").
        product_id: An ODE product id pattern the set is narrowed to, such as
            "[mh]sp*", or None for the whole product type.
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

        Raises:
            ValueError: When the triple does not carry exactly three parts.
        """
        triple, _, pattern = key.partition(":")
        parts = triple.split("/")
        if len(parts) != 3 or not all(part.strip() for part in parts):
            raise ValueError(
                f"instrument set should be IHID/IID/PT or IHID/IID/PT:PATTERN, "
                f"found {key!r}"
            )
        return cls(
            *(part.strip() for part in parts), product_id=pattern.strip() or None
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
            The identifiers joined by underscores, with everything a path
            cannot carry replaced by dashes.
        """
        raw = f"{self.ihid}_{self.iid}_{self.pt}"
        if self.product_id:
            raw = f"{raw}_{_PATTERN_PUNCTUATION.sub('', self.product_id)}"
        return raw.replace("/", "-").replace(" ", "-")

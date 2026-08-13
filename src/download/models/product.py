"""Product record and instrument catalog entry models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

ProductRecord: TypeAlias = dict[str, Any]


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

"""Checking the requested instrument sets against what ODE says it holds."""

from __future__ import annotations

from collections.abc import Sequence

from models.instrument import InstrumentSet
from models.product import InstrumentSetInfo


def _fault(info: InstrumentSetInfo | None) -> str | None:
    """Return why a set cannot be measured, or None when it can.

    Args:
        info: The catalogue entry for the set, or None when ODE has no such
            instrument host, instrument, and product type.

    Returns:
        The reason the set is unusable, or None.
    """
    if info is None:
        return "ODE holds no such instrument host, instrument and product type"
    if not info.valid_footprints:
        return "ODE publishes no footprints for it"
    if not info.valid_observation_times:
        return "ODE publishes no acquisition times for it"
    return None


def verify_sets(
    requested: Sequence[InstrumentSet], catalogued: Sequence[InstrumentSetInfo]
) -> None:
    """Refuse to run a set ODE says carries no footprint or no time.

    Coverage needs a footprint to draw the ground and a time to place it on the
    axis, and ODE states per product type whether it publishes either. Asked
    for one that does not, the run would download every record and then discard
    every record, which reads as a set that was simply never observed. It cost
    48,909 CRISM mosaic tiles before it was noticed, so it is checked up front
    against the catalogue rather than inferred afterwards from an empty result.

    A narrowed set is checked on its product type, since a product id pattern
    selects among the records of one type and cannot change what the type
    publishes.

    Args:
        requested: The instrument sets a run was asked for.
        catalogued: The instrument set catalogue as ODE reports it.

    Returns:
        None.

    Raises:
        ValueError: When any requested set cannot carry a coverage measurement.
    """
    known = {(info.ihid, info.iid, info.pt): info for info in catalogued}
    faults = [
        f"  {instrument_set.key}: {fault}"
        for instrument_set in requested
        if (
            fault := _fault(
                known.get((instrument_set.ihid, instrument_set.iid, instrument_set.pt))
            )
        )
    ]
    if faults:
        listed = "\n".join(faults)
        raise ValueError(
            f"{len(faults)} requested instrument set(s) cannot be measured:\n{listed}"
        )

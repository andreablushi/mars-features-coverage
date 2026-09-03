"""Checking the requested instrument sets against what ODE says it holds."""

from __future__ import annotations

from collections.abc import Sequence

from analysis.models.instrument import InstrumentSet, InstrumentSetInfo


def verify_sets(
    requested: Sequence[InstrumentSet], catalogued: Sequence[InstrumentSetInfo]
) -> None:
    """Refuse to run a set ODE says carries no footprint or no time.

    Args:
        requested: The instrument sets a run was asked for.
        catalogued: The instrument set catalogue as ODE reports it.

    Returns:
        None.

    Raises:
        ValueError: When any requested set cannot carry a coverage measurement.
    """
    known = {(info.ihid, info.iid, info.pt): info for info in catalogued}
    faults: list[str] = []
    for instrument_set in requested:
        info = known.get((instrument_set.ihid, instrument_set.iid, instrument_set.pt))
        if info is None:
            fault = "ODE holds no such instrument host, instrument and product type"
        elif not info.valid_footprints:
            fault = "ODE publishes no footprints for it"
        elif not info.valid_observation_times:
            fault = "ODE publishes no acquisition times for it"
        else:
            continue
        faults.append(f"  {instrument_set.key}: {fault}")
    if faults:
        listed = "\n".join(faults)
        raise ValueError(
            f"{len(faults)} requested instrument set(s) cannot be measured:\n{listed}"
        )

"""Default download selections, kept in one place so they are easy to change."""

from __future__ import annotations

from mars_remote_sensing_pipeline.ode.models import InstrumentSet

DEFAULT_INSTRUMENT_SETS: tuple[InstrumentSet, ...] = (
    InstrumentSet("MRO", "CTX", "EDR"),
    InstrumentSet("MRO", "HIRISE", "RDRV11"),
    InstrumentSet("MRO", "HIRISE", "DTM"),
    InstrumentSet("MRO", "CRISM", "MTRDR"),
    InstrumentSet("MRO", "CRISM", "TRDR"),
    InstrumentSet("MRO", "SHARAD", "RDR"),
    InstrumentSet("MGS", "MOLA", "MEGDR"),
    InstrumentSet("MEX", "HRSC", "DTMRDR"),
)

TEST_FEATURE_NAMES: tuple[str, ...] = ("Gale", "Baetis Chasma", "Jezero")

TEST_INSTRUMENT_SETS: tuple[InstrumentSet, ...] = (
    InstrumentSet("MRO", "CTX", "EDR"),
    InstrumentSet("MRO", "CRISM", "MTRDR"),
)

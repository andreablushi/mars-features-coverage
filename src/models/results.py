"""The rows a coverage computation produces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from models.instrument import InstrumentSet


@dataclass(frozen=True, slots=True)
class Event:
    """One row of the per-observation coverage record.

    Attributes:
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.
        ihid: The instrument host identifier.
        iid: The instrument identifier.
        pt: The product type.
        pdsid: The PDS product identifier.
        t_start: When the observation started.
        t_stop: When the observation finished, or None when none was published.
        own_km2: Ground this footprint covers inside the feature.
        new_km2: Ground its instrument set had not covered before, or None
            when the run kept no running union.
        cum_km2: Ground its instrument set has covered including this one,
            or None when the run kept no running union.
        cum_frac: The same as a share of the feature, or None.
        width_km: The swath width used, or None when the footprint had area.
        mask: The feature's cells this footprint fills, packed as a bitmap or
            as a list of cells, whichever is smaller, so any set of
            observations can be unioned by merging their cells.
    """

    feature_class: str
    feature_name: str
    ihid: str
    iid: str
    pt: str
    pdsid: str
    t_start: datetime
    t_stop: datetime | None
    own_km2: float
    new_km2: float | None
    cum_km2: float | None
    cum_frac: float | None
    width_km: float | None
    mask: bytes


@dataclass(frozen=True, slots=True)
class Summary:
    """One row of the per-instrument-set coverage summary.

    Attributes:
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.
        set_key: The instrument set the records were asked for by, which names
            the observing mode when a run narrowed one product type to it.
        ihid: The instrument host identifier.
        iid: The instrument identifier.
        pt: The product type.
        feature_area_km2: The area of the feature's bounding box.
        covered_km2: How much of it the set reached, or None when the run
            kept no running union.
        covered_frac: The same as a share of the feature, or None.
        n_obs: How many observations the row covers.
        t_first: When the earliest of them started.
        t_last: When the latest of them started.
        span_days: How long the row's observations span.
        mask_cells: How many of the feature's grid cells fall inside it, which
            is what a count of covered cells is a share of.
    """

    feature_class: str
    feature_name: str
    set_key: str
    ihid: str
    iid: str
    pt: str
    feature_area_km2: float
    covered_km2: float | None
    covered_frac: float | None
    n_obs: int
    t_first: datetime
    t_last: datetime
    span_days: float
    mask_cells: int


@dataclass(frozen=True, slots=True)
class SetCoverage:
    """What one instrument set covered of one feature.

    Attributes:
        events: The set's observations in chronological order.
        summary: The single row describing the set as a whole.
        pending: Whether the set has records downloaded but never measured,
            which is why it carries no observations here. False for a set that
            was measured, and for one that genuinely saw nothing.
    """

    events: list[Event]
    summary: Summary
    pending: bool = False

    @property
    def label(self) -> str:
        """Return the short readable name for the instrument set.

        Returns:
            The instrument and product type, such as "CTX EDR", carrying the
            pattern when the set is only one observing mode of that type.
        """
        return InstrumentSet.from_key(self.summary.set_key).label

    @property
    def observed(self) -> bool:
        """Report whether the set holds any observation of this feature.

        Returns:
            True when the set has at least one observation.
        """
        return bool(self.events)

    @property
    def reason(self) -> str:
        """Return why the set holds nothing to draw.

        Returns:
            What is missing, or an empty string when the set was observed.
        """
        if self.observed:
            return ""
        return "downloaded, not yet measured" if self.pending else "no observations"

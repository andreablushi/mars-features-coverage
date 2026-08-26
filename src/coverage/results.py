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
        new_km2: Ground its instrument set had not covered before.
        cum_km2: Ground its instrument set has covered including this one.
        cum_frac: The same as a share of the feature.
        width_km: The swath width used, or None when the footprint had area.
        pixels: How many of the instrument's pixels landed inside the feature.
        mask: The feature's cells this footprint fills, packed as a bitmap or a list.
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
    new_km2: float
    cum_km2: float
    cum_frac: float
    width_km: float | None
    pixels: float
    mask: bytes


@dataclass(frozen=True, slots=True)
class Summary:
    """One row of the per-instrument-set coverage summary.

    Attributes:
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.
        set_key: The instrument set the records were asked for by.
        ihid: The instrument host identifier.
        iid: The instrument identifier.
        pt: The product type.
        feature_area_km2: The area of the feature's bounding box.
        covered_km2: How much of it the set reached.
        covered_frac: The same as a share of the feature.
        n_obs: How many observations the row covers.
        t_first: When the earliest of them started.
        t_last: When the latest of them started.
        span_days: How long the row's observations span.
        mask_cells: How many of the feature's grid cells fall inside it.
        grid_side: How many cells the feature's grid holds along each axis.
        tiles_across: How many tiles the feature was cut into along each axis.
        cell_km2: How much ground one cell of that grid covers.
        grid_mask: Which cells of that grid fall inside the feature, packed as a mask.
        pixels: How many pixels the set landed inside the feature, revisits counted.
    """

    feature_class: str
    feature_name: str
    set_key: str
    ihid: str
    iid: str
    pt: str
    feature_area_km2: float
    covered_km2: float
    covered_frac: float
    n_obs: int
    t_first: datetime
    t_last: datetime
    span_days: float
    mask_cells: int
    pixels: float
    grid_side: int
    tiles_across: int
    cell_km2: float
    grid_mask: bytes


@dataclass(frozen=True, slots=True)
class SetCoverage:
    """What one instrument set covered of one feature.

    Attributes:
        events: The set's observations in chronological order.
        summary: The single row describing the set as a whole.
        pending: Whether the set has records downloaded but never measured.
    """

    events: list[Event]
    summary: Summary
    pending: bool = False

    @property
    def label(self) -> str:
        """Return the short readable name for the instrument set.

        Returns:
            The instrument and product type, such as "CTX EDR", with any pattern.
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

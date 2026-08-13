"""The rows a coverage computation produces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
        width_source: Where the swath width came from, or None.
        gridded: Whether the observation is a whole-planet basemap.
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
    width_source: str | None
    gridded: bool


@dataclass(frozen=True, slots=True)
class Summary:
    """One row of the per-instrument-set coverage summary.

    Attributes:
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.
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
        gridded: Whether the row describes a whole-planet basemap.
    """

    feature_class: str
    feature_name: str
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
    gridded: bool

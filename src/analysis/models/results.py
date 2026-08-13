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
        t_stop: When the observation finished.
        own_km2: Ground this footprint covers inside the feature.
        new_km2: Ground its instrument set had not covered before.
        cum_km2: Ground its instrument set has covered including this one.
        cum_frac: The same as a share of the feature.
        new_all_km2: Ground no instrument had covered before.
        cum_all_frac: The share every instrument together has covered so far.
        contributed: Whether the observation added anything new to its set.
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
    t_stop: datetime
    own_km2: float
    new_km2: float
    cum_km2: float
    cum_frac: float
    new_all_km2: float
    cum_all_frac: float
    contributed: bool
    width_km: float | None
    width_source: str | None
    gridded: bool


@dataclass(frozen=True, slots=True)
class Summary:
    """One row of the per-instrument-set coverage summary.

    Attributes:
        feature_class: The feature class, such as Crater or Collis.
        feature_name: The feature name as ODE spells it.
        ihid: The instrument host identifier, or ALL for the pooled row.
        iid: The instrument identifier, or ALL for the pooled row.
        pt: The product type, or ALL for the pooled row.
        feature_area_km2: The area of the feature's bounding box.
        covered_km2: How much of it the set reached.
        covered_frac: The same as a share of the feature.
        n_obs: How many observations the row covers.
        n_contributing: How many of them added ground nothing had covered.
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
    n_contributing: int
    t_first: datetime | None
    t_last: datetime | None
    span_days: float | None
    gridded: bool

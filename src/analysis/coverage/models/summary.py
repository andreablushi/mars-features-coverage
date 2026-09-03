"""The one row describing what an instrument set covered of a feature."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
        pixels: How many pixels the set landed inside the feature, revisits counted.
        grid_side: How many cells the feature's grid holds along each axis.
        cell_km2: How much ground one cell of that grid covers.
        grid_mask: Which cells of that grid fall inside the feature, packed as a mask.
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
    cell_km2: float
    grid_mask: bytes

"""Parquet schemas for the coverage artifacts.

Both schemas are declared rather than inferred. A feature whose observations
happen to carry no swath width would otherwise write a column typed differently
from its neighbours, and the per-feature files could no longer be read back as
one dataset.
"""

from __future__ import annotations

import pyarrow as pa

_TIMESTAMP = pa.timestamp("us", tz="UTC")

EVENTS = pa.schema(
    [
        ("feature_class", pa.string()),
        ("feature_name", pa.string()),
        ("ihid", pa.string()),
        ("iid", pa.string()),
        ("pt", pa.string()),
        ("pdsid", pa.string()),
        ("t_start", _TIMESTAMP),
        ("t_stop", _TIMESTAMP),
        ("own_km2", pa.float64()),
        ("new_km2", pa.float64()),
        ("cum_km2", pa.float64()),
        ("cum_frac", pa.float64()),
        ("width_km", pa.float64()),
        ("width_source", pa.string()),
    ]
)

SUMMARY = pa.schema(
    [
        ("feature_class", pa.string()),
        ("feature_name", pa.string()),
        ("ihid", pa.string()),
        ("iid", pa.string()),
        ("pt", pa.string()),
        ("feature_area_km2", pa.float64()),
        ("covered_km2", pa.float64()),
        ("covered_frac", pa.float64()),
        ("n_obs", pa.int64()),
        ("t_first", _TIMESTAMP),
        ("t_last", _TIMESTAMP),
        ("span_days", pa.float64()),
    ]
)

GEOMETRY = pa.schema(
    [
        ("feature_class", pa.string()),
        ("feature_name", pa.string()),
        ("min_lat", pa.float64()),
        ("max_lat", pa.float64()),
        ("west_lon", pa.float64()),
        ("east_lon", pa.float64()),
        ("pdsid", pa.string()),
        ("ihid", pa.string()),
        ("iid", pa.string()),
        ("pt", pa.string()),
        ("t_start", _TIMESTAMP),
        ("t_stop", _TIMESTAMP),
        ("width_km", pa.float64()),
        ("width_source", pa.string()),
        ("wkb", pa.binary()),
    ]
)

"""Parquet schemas for the coverage artifacts."""

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
        ("mask", pa.binary()),
    ]
)

SUMMARY = pa.schema(
    [
        ("feature_class", pa.string()),
        ("feature_name", pa.string()),
        ("set_key", pa.string()),
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
        ("mask_cells", pa.int64()),
    ]
)

"""Accumulating spatial coverage through time for one feature.

Observations are walked once, in chronological order across every instrument
set at once. Each is projected a single time and folded into two running
unions: the one for its own instrument set, and the one pooling every
instrument.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from analysis import configs
from analysis.computation import footprints, geodesy, swath
from analysis.computation.region import CoverageUnion, FeatureRegion
from analysis.models.feature import FeatureBox
from analysis.models.observation import Observation
from analysis.models.results import Event, Summary


def compute(
    box: FeatureBox, observations: Sequence[Observation]
) -> tuple[list[Event], list[Summary]]:
    """Measure how each instrument set covers one feature over time.

    Args:
        box: The feature bounding box coverage is measured against.
        observations: The feature's observations in chronological order.

    Returns:
        One event row per observation and one summary row per instrument set,
        with a pooled row across every set appended to the summaries.
    """
    region = FeatureRegion(box.min_lat, box.max_lat, box.west_lon, box.east_lon)
    widths = _track_widths(observations)
    pooled = CoverageUnion()
    seen: dict[tuple[str, str, str], CoverageUnion] = {}
    events: list[Event] = []

    for observation in observations:
        key = observation.set_key
        width_m, source = widths.get(observation.pdsid, (0.0, None))
        shape = region.footprint(footprints.parse(observation.wkt), width_m)
        covered = seen.setdefault(key, CoverageUnion())
        fresh_m2 = covered.add(shape)
        gridded = key in configs.GRIDDED_SETS
        pooled_fresh_m2 = 0.0 if gridded else pooled.add(shape)
        events.append(
            Event(
                feature_class=box.feature_class,
                feature_name=box.name,
                ihid=observation.ihid,
                iid=observation.iid,
                pt=observation.pt,
                pdsid=observation.pdsid,
                t_start=observation.start,
                t_stop=observation.stop,
                own_km2=shape.area / 1e6,
                new_km2=fresh_m2 / 1e6,
                cum_km2=covered.area_m2 / 1e6,
                cum_frac=covered.area_m2 / region.area_m2,
                new_all_km2=pooled_fresh_m2 / 1e6,
                cum_all_frac=pooled.area_m2 / region.area_m2,
                contributed=fresh_m2 > 0.0,
                width_km=width_m / 1000.0 if source else None,
                width_source=source,
                gridded=gridded,
            )
        )

    summaries = _summaries(box, events, pooled.area_m2, region.area_m2)
    return events, summaries


def _track_widths(
    observations: Sequence[Observation],
) -> dict[str, tuple[float, str]]:
    """Derive a swath width for every ground track in the feature.

    Args:
        observations: The feature's observations.

    Returns:
        The width in metres and its source, keyed by product identifier, for
        the track footprints only.
    """
    tracks = [observation for observation in observations if observation.is_track]
    if not tracks:
        return {}
    measurements = [
        (_track_length(observation.wkt), observation.duration_s)
        for observation in tracks
    ]
    resolved = swath.resolve_widths(measurements)
    return {
        observation.pdsid: width
        for observation, width in zip(tracks, resolved, strict=True)
    }


def _track_length(wkt: str) -> float:
    """Return the full ground length of a track footprint.

    The whole track is measured, not the part inside the feature, because the
    length is only used with the observation's duration to recover the ground
    speed the spacecraft flew at.

    Args:
        wkt: The footprint as well-known text.

    Returns:
        The summed length in metres.
    """
    total = 0.0
    for part in footprints.flatten(footprints.parse(wkt)):
        if part.geom_type != "LineString":
            continue
        coords = np.asarray(part.coords)
        total += geodesy.haversine_length(coords[:, 0], coords[:, 1])
    return total


def _summaries(
    box: FeatureBox,
    events: Sequence[Event],
    pooled_m2: float,
    total_m2: float,
) -> list[Summary]:
    """Roll the events up into one row per instrument set, plus the pool.

    The pooled row leaves out whole-planet basemaps. Including them would put
    it at full coverage from its first event onwards and say nothing about what
    the targeted instruments actually reached.

    Args:
        box: The feature being covered.
        events: The event rows produced for it.
        pooled_m2: Ground covered by every non-basemap set together.
        total_m2: The area of the whole feature.

    Returns:
        One summary row per instrument set followed by the pooled row.
    """
    grouped: dict[tuple[str, str, str], list[Event]] = {}
    for event in events:
        grouped.setdefault((event.ihid, event.iid, event.pt), []).append(event)

    rows = [
        _summary(
            box, key, total_m2, member, member[-1].cum_frac, key in configs.GRIDDED_SETS
        )
        for key, member in sorted(grouped.items())
    ]
    label = configs.ALL_SETS_LABEL
    targeted = [event for event in events if not event.gridded]
    rows.append(
        _summary(
            box,
            (label, label, label),
            total_m2,
            targeted,
            pooled_m2 / total_m2,
            False,
            contributing=sum(event.new_all_km2 > 0.0 for event in targeted),
        )
    )
    return rows


def _summary(
    box: FeatureBox,
    key: tuple[str, str, str],
    total_m2: float,
    member: Sequence[Event],
    covered_frac: float,
    gridded: bool,
    contributing: int | None = None,
) -> Summary:
    """Build one summary row from the events it covers.

    Args:
        box: The feature being covered.
        key: The instrument host, instrument, and product type.
        total_m2: The area of the whole feature.
        member: The events the row rolls up, in chronological order.
        covered_frac: The share of the feature the row ended up covering.
        gridded: Whether the row describes a whole-planet basemap.
        contributing: How many events added new ground, counted against the
            pool rather than against the row's own instrument set.

    Returns:
        The summary row.
    """
    area_km2 = total_m2 / 1e6
    first = member[0].t_start if member else None
    last = member[-1].t_start if member else None
    return Summary(
        feature_class=box.feature_class,
        feature_name=box.name,
        ihid=key[0],
        iid=key[1],
        pt=key[2],
        feature_area_km2=area_km2,
        covered_km2=covered_frac * area_km2,
        covered_frac=covered_frac,
        n_obs=len(member),
        n_contributing=(
            contributing
            if contributing is not None
            else sum(event.contributed for event in member)
        ),
        t_first=first,
        t_last=last,
        span_days=(last - first).total_seconds() / 86400.0 if first and last else None,
        gridded=gridded,
    )

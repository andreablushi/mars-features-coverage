"""Selecting the dataset: one feature searched, every one searched, what is kept.

This is the whole selection stage. A feature earns a place or it does not, and
the observations the ones that do keep are written down by name, so a later run
knows what to download and what to leave alone without searching again.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor

from analysis.coverage.artifacts import indexing
from analysis.coverage.models.coverage import SetCoverage
from analysis.selector import algorithm
from analysis.selector.artifacts import filter_config as filtering
from analysis.selector.artifacts import write
from analysis.selector.filters.clean_window import clean_window
from analysis.selector.models import track as timeline
from analysis.selector.models.filter import Filter
from analysis.selector.models.grid import Grid
from analysis.selector.models.selection import (
    SelectedFeature,
    SelectedObservation,
    Selection,
)
from analysis.selector.models.survey import Study
from analysis.utils.maths import mask as packing

# One feature, as the catalogue spells its class and its name
FeatureName = tuple[str, str]
# Called with how many features are searched and how many there are
Progress = Callable[[int, int], None]


def select_dataset(workers: int, progress: Progress | None = None) -> list[Selection]:
    """Search every measured feature under the filter, and write the selection out.

    Args:
        workers: How many processes to search on at once, as the run is configured.
        progress: Called with how many features are searched and how many there are.

    Returns:
        What the search left of each feature, in catalogue order.
    """
    named = indexing.catalogued_features()
    picked = search_features(named, selected, workers, progress)
    write.write_selection(picked)
    return picked


def search_features[T](
    features: Sequence[FeatureName],
    read: Callable[[FeatureName, Study], T],
    workers: int,
    progress: Progress | None = None,
) -> list[T]:
    """Search every named feature under the written filter, on many processes.

    A search costs far more than the observations a feature holds, and the busiest
    features are a handful, so they are searched first. One of them starting last
    would run on alone for hours after the rest of the pool had drained.

    A whole study is far heavier than anything read off it, so each worker reads
    its own and sends back only what the caller asked for.

    Args:
        features: The features to search, as class and name.
        read: What to make of each feature's search, run inside the worker.
        workers: How many processes to search on at once, as the run is configured.
        progress: Called with how many features are done and how many there are.

    Returns:
        What was read off each search, in the order the features came in, leaving
        out a feature holding no measured set on disk.
    """
    found: list[T | None] = [None for _ in features]
    observations = indexing.catalogued_observations()
    busiest_first = sorted(
        range(len(features)), key=lambda at: -observations.get(features[at], 0)
    )
    with ProcessPoolExecutor(max_workers=workers) as pool:
        read_back = pool.map(
            _searched,
            [(read, features[at]) for at in busiest_first],
            chunksize=1,
        )
        searched = zip(busiest_first, read_back, strict=True)
        for done, (at, entry) in enumerate(searched, 1):
            found[at] = entry
            if progress is not None:
                progress(done, len(features))
    return [entry for entry in found if entry is not None]


def study_feature(coverage: Sequence[SetCoverage], criteria: Filter) -> Study:
    """Search one feature under the filter.

    Args:
        coverage: The feature's instrument sets, in any order.
        criteria: Which instruments a window has to hold, and how much ground each.

    Returns:
        What the search found, the timeline it ran over and the window it earned.
    """
    summary = coverage[0].summary
    inside = packing.cells_of(summary.grid_mask).tolist()
    grid = Grid(
        cells=summary.grid_side * summary.grid_side,
        area_km2=len(inside) * summary.cell_km2,
        cell_km2=summary.cell_km2,
        inside=frozenset(inside),
    )
    # The one place the filter is read, which everything below takes it from
    settled = clean_window(criteria, coverage, grid)
    track = timeline.build(coverage, grid, settled)
    return Study(
        criteria=settled,
        track=track,
        survey=algorithm.search(track, settled) if track else None,
    )


def selected(feature: FeatureName, study: Study) -> Selection:
    """Read one feature's search as the rows the selection is written from.

    Args:
        feature: The feature's class and name, as the catalogue spells them.
        study: What the search found over it.

    Returns:
        Its own row, and a row for each observation it keeps.
    """
    feature_class, name = feature
    survey, track = study.survey, study.track
    row = SelectedFeature(
        feature_class=feature_class,
        feature_name=name,
        kept=survey is not None,
        area_km2=track.grid.area_km2 if track else 0.0,
        start=survey.start if survey else None,
        end=survey.end if survey else None,
        days=survey.days if survey else 0.0,
        geo_mean=survey.geo_mean if survey else 0.0,
        taken=len(survey.taken) if survey else 0,
    )
    if survey is None or track is None:
        return Selection(feature=row)
    standing = set(survey.standing)
    return Selection(
        feature=row,
        observations=[
            SelectedObservation(
                feature_class=feature_class,
                feature_name=name,
                ihid=track.observations[index].ihid,
                iid=track.observations[index].iid,
                pt=track.observations[index].pt,
                pdsid=track.observations[index].pdsid,
                t_start=track.observations[index].t_start,
                standing=index in standing,
            )
            for index in survey.taken
        ],
    )


def _searched[T](
    job: tuple[Callable[[FeatureName, Study], T], FeatureName],
) -> T | None:
    """Search one feature and read what the caller asked off it.

    Args:
        job: What to make of the search, and the feature's class and name.

    Returns:
        What was read off it, and None where it has no measured set on disk.
    """
    read, feature = job
    coverage = indexing.load_feature(*feature)
    if not coverage:
        return None
    return read(feature, study_feature(coverage, filtering.FILTER))

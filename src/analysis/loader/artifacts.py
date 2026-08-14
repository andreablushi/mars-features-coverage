"""Reading finished coverage artifacts back off disk.

The rows are read under the declared schemas rather than as whatever the files
happen to hold, so a file written by an older run loads as the rows this stage
defines today or not at all.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from analysis import configs
from analysis.loader import layout
from analysis.models.coverage import SetCoverage
from analysis.models.results import Event, Summary
from analysis.models.schemas import EVENTS, SUMMARY


def computed_features(root: Path = configs.COVERAGE_ROOT) -> set[tuple[str, str]]:
    """Return every feature that has coverage computed locally.

    Args:
        root: The coverage artifacts root directory.

    Returns:
        The class and name slug of each feature holding at least one computed
        instrument set.
    """
    return {
        (path.parent.parent.name, path.parent.name)
        for path in root.glob(f"*/*/*{configs.EVENTS_SUFFIX}")
    }


def load_feature(
    feature_class: str, name: str, root: Path = configs.COVERAGE_ROOT
) -> list[SetCoverage]:
    """Read every computed instrument set for one feature.

    Args:
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.
        root: The coverage artifacts root directory.

    Returns:
        One entry per finished instrument set, widest coverage first. A run
        that kept no union measured no coverage to rank by, so those sets fall
        back to the busiest first.
    """
    directory = layout.feature_artifacts_dir(root, feature_class, name)
    loaded = [
        _load_set(path) for path in sorted(directory.glob(f"*{configs.EVENTS_SUFFIX}"))
    ]
    return sorted(
        (entry for entry in loaded if entry),
        key=lambda entry: (-(entry.summary.covered_frac or 0.0), -entry.summary.n_obs),
    )


def _load_set(events_path: Path) -> SetCoverage | None:
    """Read one instrument set's events and summary.

    Args:
        events_path: The set's events parquet file.

    Returns:
        The set's coverage, or None when its summary is missing, which marks a
        set whose computation never finished.
    """
    summary_path = events_path.with_name(
        events_path.name.replace(configs.EVENTS_SUFFIX, configs.SET_SUMMARY_SUFFIX)
    )
    if not summary_path.exists():
        return None
    summary = pq.read_table(summary_path, schema=SUMMARY).to_pylist()
    events = pq.read_table(events_path, schema=EVENTS).to_pylist()
    return SetCoverage(
        events=[Event(**row) for row in events], summary=Summary(**summary[0])
    )

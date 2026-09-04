"""Turning one downloaded product into every crop the features kept it for."""

from __future__ import annotations

from pathlib import Path

import utils.disk.paths as paths
from building.instruments import INSTRUMENTS
from building.metadata import record
from building.metadata.models.observation import ObservationRecord
from building.models.job import Job, Outcome


def build(job: Job, root: Path = paths.DATASET_ROOT) -> Outcome:
    """Cut one downloaded product to every feature that kept it, and write each.

    The product is read and cleaned once however many features want it, which is
    what makes the product rather than the feature the unit of work.

    Args:
        job: The product to build, and the features to cut it to.
        root: The dataset's own root directory.

    Returns:
        The outcome, holding the records of what was written or the error that
        stopped it, which is never raised so a pool can collect it.
    """
    steps = INSTRUMENTS[job.instrument]
    try:
        sample = steps.sample(job.identifier)
    except Exception as error:  # noqa: BLE001
        return Outcome(job, error=error)
    written: list[ObservationRecord] = []
    missed = 0
    for frame in job.frames:
        try:
            held = steps.crop(sample, steps.place(sample, frame), frame)
        except Exception as error:  # noqa: BLE001
            return Outcome(job, records=tuple(written), error=error)
        # A product reaching none of a feature is no failure: the coverage it
        # was kept for is a box overlap, and a crop can still come out empty.
        if held is None:
            missed += 1
            continue
        path = steps.write(held, frame, root)
        written.append(
            record.observation_record(
                held,
                frame,
                steps.layout,
                job.identifier,
                str(path.relative_to(root)),
                t_start=job.t_start,
                altitude=steps.altitude(held.sample) if steps.altitude else None,
            )
        )
    return Outcome(job, records=tuple(written), missed=missed)

"""Turning one downloaded product into every crop the features kept it for."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import utils.disk.paths as paths
from building.configs import crism as crism_configs
from building.configs import ctx as ctx_configs
from building.configs import mola as mola_configs
from building.configs import sharad as sharad_configs
from building.crop.crism import crop as crism_crop
from building.crop.ctx import crop as ctx_crop
from building.crop.mola import crop as mola_crop
from building.crop.sharad import crop as sharad_crop
from building.geometry.crism import place as crism_place
from building.geometry.ctx import place as ctx_place
from building.geometry.mola import place as mola_place
from building.geometry.sharad import altitude
from building.geometry.sharad import place as sharad_place
from building.metadata import record  # noqa: I001
from building.metadata.models.observation import ObservationRecord
from building.models.job import Job, Outcome
from building.preprocessing.crism import read as crism_read
from building.preprocessing.crism.correction import merge_detectors
from building.preprocessing.ctx import read as ctx_read
from building.preprocessing.mola import read as mola_read
from building.preprocessing.sharad import read as sharad_read
from building.writing.crism import crop as crism_write
from building.writing.ctx import crop as ctx_write
from building.writing.mola import crop as mola_write
from building.writing.sharad import crop as sharad_write


@dataclass(frozen=True, slots=True)
class Steps:
    """How one instrument goes from a product on disk to a crop in the dataset.

    Attributes:
        sample: What reads the product off disk into the instrument's own sample.
        place: What places that sample against one feature.
        crop: What cuts it to that feature.
        write: What writes the crop into the dataset.
        axes: What each axis of the measurement holds.
        measurement: The name the measurement is written under.
    """

    sample: Callable[[str], Any]
    place: Callable[..., Any]
    crop: Callable[..., Any]
    write: Callable[..., Path]
    axes: tuple[str, ...]
    measurement: str


def _crism_sample(identifier: str):
    """Read one CRISM observation, clean it, and join its two detectors."""
    return merge_detectors.merge_detectors(crism_read.clean(identifier))


STEPS = {
    "CRISM": Steps(
        _crism_sample,
        crism_place.place,
        crism_crop.crop,
        crism_write.write,
        crism_configs.AXES,
        crism_write.MEASUREMENT,
    ),
    "CTX": Steps(
        ctx_read.read,
        ctx_place.place,
        ctx_crop.crop,
        ctx_write.write,
        ctx_configs.AXES,
        ctx_write.MEASUREMENT,
    ),
    "MOLA": Steps(
        mola_read.read,
        mola_place.place,
        mola_crop.crop,
        mola_write.write,
        mola_configs.AXES,
        mola_write.MEASUREMENT,
    ),
    "SHARAD": Steps(
        sharad_read.read,
        sharad_place.place,
        sharad_crop.crop,
        sharad_write.write,
        sharad_configs.AXES,
        sharad_write.MEASUREMENT,
    ),
}


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
    steps = STEPS[job.instrument]
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
                frame,
                job.instrument,
                job.identifier,
                str(path.relative_to(root)),
                steps.axes,
                tuple(getattr(held.sample, steps.measurement).shape),
                held.placement,
                t_start=job.t_start,
                altitude=altitude.altitude_m(held.sample)
                if job.instrument == "SHARAD"
                else None,
            )
        )
    return Outcome(job, records=tuple(written), missed=missed)

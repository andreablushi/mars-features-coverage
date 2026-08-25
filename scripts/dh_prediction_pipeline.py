#!/usr/bin/env python
"""Predict the dataset on DigitalHub: what the platform calls, and what submits it."""

from __future__ import annotations

import os
import tarfile
from pathlib import Path

import dh_pipeline
import digitalhub as dh
from digitalhub_runtime_python import handler

import console
import utils.disk.paths as paths
import utils.disk.settings as settings
from storage import summary
from survey import strategies
from visualization.dataset import loading, saving
from visualization.dataset.stats import dataset

FUNCTION_NAME = "features-prediction"
HANDLER = "scripts.dh_prediction_pipeline:save_predictions"

PREDICTIONS_NAME = "coverage-predictions"


@handler(outputs=[PREDICTIONS_NAME])
def save_predictions(project):
    """Sweep the measurements already published and publish what they predict.

    Nothing is measured here. The measurements a previous run left on the
    platform are fetched, every strategy written is searched over every tile
    of every feature in them, and what each strategy would make of the dataset
    is published so a notebook can read it without sweeping again.

    Args:
        project: The DigitalHub project, injected by the runtime, which the
            measurements are read from and the prediction is logged into.

    Returns:
        The uploaded archive of the prediction.

    Raises:
        RuntimeError: When the published measurements hold no feature to
            search, which means there is nothing to predict from.
    """
    os.environ[console.PLAIN_LOG_ENV] = "1"
    print("fetching the measurements", flush=True)
    _unpack(project.get_artifact(dh_pipeline.ARTIFACTS_NAME).download(overwrite=True))

    named = summary.catalogued_features()
    if not named:
        raise RuntimeError("the published measurements hold no feature to search")
    workers = settings.load().workers
    print(
        f"sweeping {len(named):,} features under {len(strategies.STRATEGIES)} "
        f"strategies on {workers} workers",
        flush=True,
    )
    found = loading.sweep(list(strategies.STRATEGIES), named, workers)
    saving.written(dataset.read(found))

    print("uploading the prediction", flush=True)
    packed = dh_pipeline.archive(paths.PREDICTIONS_ROOT, PREDICTIONS_NAME)
    prediction = project.log_artifact(
        name=PREDICTIONS_NAME,
        kind="artifact",
        source=str(packed),
        description="What each strategy would make of the dataset; unpack under data/.",
    )
    print("done", flush=True)
    return prediction


def _unpack(downloaded: str) -> None:
    """Put the published measurements back where the search reads them.

    Args:
        downloaded: Where the platform left the archive, which is either the
            archive itself or the directory holding it.

    Returns:
        None.

    Raises:
        RuntimeError: When the download left no archive to unpack.
    """
    path = Path(downloaded)
    if path.is_dir():
        found = sorted(path.glob("*.tar.gz"))
        if not found:
            raise RuntimeError(f"no measurements were downloaded into {path}")
        path = found[0]
    paths.DATA_ROOT.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path) as packed:
        packed.extractall(paths.DATA_ROOT, filter="data")


def main() -> int:
    """Register a version of the prediction from a pushed commit, and run it.

    Returns:
        A process exit code, non zero when the image did not build. The job is
        never waited on, so its own outcome is read from the platform.
    """
    arguments = dh_pipeline.parser().parse_args()

    # Register a version of the function pointing at the pushed ref.
    project = dh.get_or_create_project(arguments.project)
    function = project.new_function(
        name=FUNCTION_NAME,
        kind="python",
        python_version=dh_pipeline.PYTHON_VERSION,
        code_src=f"git+{dh_pipeline.REPOSITORY}#{arguments.ref}",
        handler=HANDLER,
        requirements=dh_pipeline.requirements(),
    )

    # Build the image first, since the job cannot install anything itself.
    built = function.run(action="build", wait=True)
    if built.status.state != dh_pipeline.COMPLETED:
        print(f"the image did not build: {built.status.state}")
        return 1
    function.refresh()

    # Start the job on the built image, telling it where the clone lands.
    root = dh_pipeline.SOURCE_ROOT
    run = function.run(
        action="job",
        resources={
            "cpu": arguments.cpu or str(settings.load().workers),
            "mem": arguments.mem,
            "disk": arguments.disk,
        },
        envs=[{"name": "PYTHONPATH", "value": f"{root}:{root}/src:{root}/scripts"}],
        wait=False,
    )
    print(run.key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

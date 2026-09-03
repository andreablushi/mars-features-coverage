#!/usr/bin/env python
"""Predict the dataset on DigitalHub: what the platform calls, and what submits it."""

from __future__ import annotations

import os
import shutil
import tarfile
from pathlib import Path

import dh_pipeline
import digitalhub as dh
from digitalhub_runtime_python import handler

import analysis.utils.settings as settings
import utils.disk.paths as paths
from analysis import console
from analysis.coverage import summary
from analysis.sampling import predicting, storing, sweeping
from analysis.selector import configs as filtering

FUNCTION_NAME = "features-prediction"
HANDLER = "scripts.dh_prediction_pipeline:save_predictions"

PREDICTIONS_NAME = "coverage-predictions"


@handler(outputs=[PREDICTIONS_NAME])
def save_predictions(project):
    """Sweep the features under the filter and publish what it predicts.

    Args:
        project: The DigitalHub project the prediction is logged into.

    Returns:
        The uploaded archive of the prediction.

    Raises:
        RuntimeError: When the published measurements hold no feature to search.
    """
    os.environ[console.PLAIN_LOG_ENV] = "1"
    print("fetching the measurements", flush=True)
    _unpack(
        project.get_artifact(dh_pipeline.ARTIFACTS_NAME).download(overwrite=True),
        paths.ARTIFACTS_ROOT,
    )

    named = summary.catalogued_features()
    if not named:
        raise RuntimeError("the published measurements hold no feature to search")
    # A sweep published under the filter as it is written now need not run again
    held = None
    if project.list_artifacts(name=PREDICTIONS_NAME):
        print("fetching the prediction published before", flush=True)
        _unpack(
            project.get_artifact(PREDICTIONS_NAME).download(overwrite=True),
            paths.PREDICTIONS_ROOT,
        )
        held = sweeping.still_current(storing.read_prediction())
        print(f"kept from it: {'the sweep' if held else 'nothing'}", flush=True)
    else:
        print("nothing was published before, sweeping the whole catalogue", flush=True)

    if held is None:
        workers = settings.load().workers
        print(
            f"sweeping {len(named):,} features under the filter on {workers} workers",
            flush=True,
        )
        held = predicting.prediction(
            sweeping.sweep(named, workers, console.logged("sweep"))
        )
    else:
        print("the filter is published as it is written, nothing to sweep", flush=True)

    written = storing.write_prediction(held, filtering.digest())
    # A file left by an older layout names no sweep, so it is cleared
    for path in sorted(paths.PREDICTIONS_ROOT.glob("*.json")):
        if path != written:
            print(f"dropping {path.name}, nothing reads it back", flush=True)
            path.unlink()

    print("uploading the prediction", flush=True)
    packed = dh_pipeline.archive(paths.PREDICTIONS_ROOT, PREDICTIONS_NAME)
    prediction = project.log_artifact(
        name=PREDICTIONS_NAME,
        kind="artifact",
        source=str(packed),
        description=(
            "What the filter would make of the dataset; unpack under data/analysis/."
        ),
    )
    print("done", flush=True)
    return prediction


def _unpack(downloaded: str, into: Path) -> None:
    """Put what was published back where the search reads it, and nothing else.

    Args:
        downloaded: The archive the platform left, or the directory holding it.
        into: The directory the archive fills, emptied first so that what it
            holds afterwards is what was published and only that.

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
    shutil.rmtree(into, ignore_errors=True)
    into.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path) as packed:
        packed.extractall(into.parent, filter="data")


def main() -> int:
    """Register a version of the prediction from a pushed commit, and run it.

    Returns:
        A process exit code, non zero when the image did not build.
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
